# Reconcile GitLab instance admins, groups, and memberships from desired state.
# Idempotent: only writes when something differs; prints one line per change.
# Read via `gitlab-rails runner`; desired state passed as JSON at ARGV[0].
require "json"

desired = JSON.parse(File.read(ARGV[0]))
root = User.find_by_username("root")
changes = 0

# --- 1. Instance admins -------------------------------------------------------
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

# --- 2. Groups ----------------------------------------------------------------
# GitLab 17+/19 requires an Organization for a new group.
default_org = Organizations::Organization.default_organization if defined?(Organizations::Organization)
(desired["groups"] || []).each do |g|
  next if Group.find_by_full_path(g["path"])
  params = {
    name: g["name"], path: g["path"], description: g["description"].to_s,
    visibility_level: Gitlab::VisibilityLevel.const_get(g["visibility"].upcase)
  }
  params[:organization_id] = default_org.id if default_org
  res = Groups::CreateService.new(root, params).execute
  grp = res.respond_to?(:payload) ? res.payload[:group] : res
  if grp&.persisted?
    changes += 1
    puts "group+ created #{g['path']}"
  else
    puts "group! FAILED #{g['path']}: #{(grp&.errors&.full_messages || res).to_a.join(', ')}"
  end
end

# --- 3. Memberships -----------------------------------------------------------
levels = { "guest" => 10, "reporter" => 20, "developer" => 30, "maintainer" => 40, "owner" => 50 }
(desired["members"] || []).each do |m|
  grp = Group.find_by_full_path(m["group"])
  u = User.find_by_username(m["username"])
  (puts "member? skip #{m['username']}/#{m['group']} (missing user or group)"; next) if grp.nil? || u.nil?
  lvl = levels[m["access"]]
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

puts "RBAC_DONE changes=#{changes}"
