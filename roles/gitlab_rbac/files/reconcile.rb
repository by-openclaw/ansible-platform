# Reconcile GitLab instance policy, admins, groups (+ subgroups), memberships,
# and project cleanup from desired state. Idempotent: writes only on diff, prints
# one line per change. Run via `gitlab-rails runner reconcile.rb desired.json`.
require "json"
require "set"

desired = JSON.parse(File.read(ARGV[0]))
root = User.find_by_username("root")
changes = 0

VIS = { "private" => 0, "internal" => 10, "public" => 20 }.freeze
PROJ_CREATE = { "noone" => 0, "maintainer" => 1, "developer" => 2 }.freeze
SUBGRP_CREATE = { "owner" => 0, "maintainer" => 1 }.freeze
LEVELS = { "guest" => 10, "reporter" => 20, "developer" => 30, "maintainer" => 40, "owner" => 50 }.freeze

# --- 1. Instance policy (ApplicationSetting) ---------------------------------
s = ApplicationSetting.current
(desired["settings"] || {}).each do |k, v|
  val =
    case k
    when "default_project_visibility", "default_group_visibility" then VIS[v]
    when "restricted_visibility_levels" then v.map { |x| VIS[x] }
    else v
    end
  next if s.public_send(k) == val
  s.public_send("#{k}=", val)
  changes += 1
  puts "setting~ #{k} = #{val.inspect}"
end
s.save! if s.changed?

# --- 2. Instance admins ------------------------------------------------------
admins = desired["instance_admins"] || []
if desired["enforce_admin_exact"]
  User.where(admin: true).where.not(username: admins + ["root"]).find_each do |u|
    next unless u.human?
    u.update!(admin: false)
    changes += 1
    puts "admin- demoted #{u.username}"
  end
end
admins.each do |un|
  u = User.find_by_username(un)
  (puts "admin? skip (no such user yet): #{un}"; next) if u.nil?
  next if u.admin?
  u.update!(admin: true)
  changes += 1
  puts "admin+ promoted #{un}"
end

# --- 3. Groups (+ subgroups) -------------------------------------------------
default_org = (Organizations::Organization.default_organization if defined?(Organizations::Organization))
(desired["groups"] || []).each do |g|
  full = g["parent"] ? "#{g['parent']}/#{g['path']}" : g["path"]
  grp = Group.find_by_full_path(full)
  if grp.nil?
    params = {
      name: g["name"], path: g["path"],
      visibility_level: VIS[g["visibility"]],
      project_creation_level: PROJ_CREATE[g["project_creation"]],
      subgroup_creation_level: SUBGRP_CREATE[g["subgroup_creation"]]
    }
    params[:organization_id] = default_org.id if default_org
    if g["parent"]
      parent = Group.find_by_full_path(g["parent"])
      params[:parent_id] = parent&.id
    end
    res = Groups::CreateService.new(root, params).execute
    grp = res.respond_to?(:payload) ? res.payload[:group] : res
    if grp&.persisted?
      changes += 1
      puts "group+ created #{full}"
    else
      puts "group! FAILED #{full}: #{(grp&.errors&.full_messages || res).to_a.join(', ')}"
      next
    end
  else
    upd = {}
    upd[:visibility_level] = VIS[g["visibility"]] if grp.visibility_level != VIS[g["visibility"]]
    upd[:project_creation_level] = PROJ_CREATE[g["project_creation"]] if grp.project_creation_level != PROJ_CREATE[g["project_creation"]]
    upd[:subgroup_creation_level] = SUBGRP_CREATE[g["subgroup_creation"]] if grp.subgroup_creation_level != SUBGRP_CREATE[g["subgroup_creation"]]
    unless upd.empty?
      grp.update!(upd)
      changes += 1
      puts "group~ #{full}: #{upd.keys.join(',')}"
    end
  end
end

# --- 4. Memberships ----------------------------------------------------------
# Desired (group_full_path, username) pairs — the exact intended direct members.
desired_pairs = (desired["members"] || []).map { |m| [m["group"], m["username"]] }.to_set
managed_paths = (desired["groups"] || []).map { |g| g["parent"] ? "#{g['parent']}/#{g['path']}" : g["path"] }

# Prune first: remove DIRECT human members of a managed group that aren't desired
# (e.g. a stale platform-level grant that would inherit down and floor a subgroup).
# Never touches root or inherited memberships. Do this before add so inheritance
# is clean when a lower direct role is then applied to a subgroup.
managed_paths.each do |path|
  grp = Group.find_by_full_path(path)
  next if grp.nil?
  grp.members.each do |mem|
    un = mem.user&.username
    next if un.nil? || un == "root" || !mem.user.human?
    next if desired_pairs.include?([path, un])
    mem.destroy!
    changes += 1
    puts "member- removed #{un} from #{path}"
  end
end

(desired["members"] || []).each do |m|
  grp = Group.find_by_full_path(m["group"])
  u = User.find_by_username(m["username"])
  (puts "member? skip #{m['username']}/#{m['group']} (missing user or group)"; next) if grp.nil? || u.nil?
  lvl = LEVELS[m["access"]]
  existing = grp.members.find_by(user_id: u.id)
  if existing.nil?
    grp.add_member(u, lvl)
    changes += 1
    puts "member+ #{m['username']} -> #{m['group']} (#{m['access']})"
  elsif existing.access_level != lvl
    existing.update!(access_level: lvl)
    changes += 1
    puts "member~ #{m['username']} in #{m['group']} -> #{m['access']}"
  end
end

# --- 5. Project cleanup ------------------------------------------------------
(desired["delete_projects"] || []).each do |fp|
  p = Project.find_by_full_path(fp)
  next if p.nil?
  Projects::DestroyService.new(p, root).execute
  changes += 1
  puts "project- deleted #{fp}"
end

# --- 6. Projects (support/desk repos) ---------------------------------------
# Create-if-absent under a group; reconcile description, visibility and the
# Service Desk flag (GitLab needs incoming_email configured for it to be live).
(desired["projects"] || []).each do |pj|
  full = "#{pj["group"]}/#{pj["path"]}"
  proj = Project.find_by_full_path(full)
  if proj.nil?
    grp = Group.find_by_full_path(pj["group"])
    if grp.nil?
      puts "project! FAILED #{full}: group #{pj["group"]} missing"
      next
    end
    params = {
      name: pj["name"], path: pj["path"], namespace_id: grp.id,
      description: pj["description"].to_s,
      visibility_level: VIS[pj["visibility"] || "private"],
      initialize_with_readme: pj.fetch("readme", true)
    }
    proj = Projects::CreateService.new(root, params).execute
    if proj&.persisted?
      changes += 1
      puts "project+ created #{full}"
    else
      puts "project! FAILED #{full}: #{proj&.errors&.full_messages.to_a.join(', ')}"
      next
    end
  end
  upd = {}
  upd[:description] = pj["description"].to_s if pj.key?("description") && proj.description.to_s != pj["description"].to_s
  upd[:visibility_level] = VIS[pj["visibility"]] if pj["visibility"] && proj.visibility_level != VIS[pj["visibility"]]
  upd[:service_desk_enabled] = pj["service_desk"] if pj.key?("service_desk") && proj.service_desk_enabled != pj["service_desk"]
  next if upd.empty?
  proj.update!(upd)
  changes += 1
  puts "project~ #{full} #{upd.keys.join(',')}"
end

# --- 7. Project integrations (Discord per project) ----------------------------
# {project, type: discord, webhook, events: {push: true, ...}, branches: default}
(desired["integrations"] || []).each do |it|
  proj = Project.find_by_full_path(it["project"])
  if proj.nil?
    puts "integration! FAILED #{it["project"]}: project missing"
    next
  end
  integ = proj.find_or_initialize_integration(it["type"])
  if integ.nil?
    puts "integration! FAILED #{it["project"]}: unknown type #{it["type"]}"
    next
  end
  want = { "webhook" => it["webhook"], "active" => true,
           "branches_to_be_notified" => (it["branches"] || "default") }
  (it["events"] || {}).each { |ev, on| want["#{ev}_events"] = on }
  diff = want.reject { |k, v| integ.respond_to?(k) && integ.public_send(k) == v }
  next if diff.empty? && integ.persisted?
  diff.each { |k, v| integ.public_send("#{k}=", v) }
  integ.save!
  changes += 1
  puts "integration~ #{it["project"]} #{it["type"]} #{diff.keys.join(',')}"
end

puts "RBAC_DONE changes=#{changes}"
