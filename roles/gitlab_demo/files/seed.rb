# Seed a demo project + its files idempotently.
#   gitlab-rails runner seed.rb <files_dir> <project_full_path> <project_name>
require "find"

dir  = ARGV[0]
full = ARGV[1]
name = ARGV[2]
u = User.find_by_username("root")

ns_path = full.rpartition("/").first
ns = Group.find_by_full_path(ns_path)
abort "no such namespace: #{ns_path}" if ns.nil?

proj = Project.find_by_full_path(full)
if proj.nil?
  res = Projects::CreateService.new(
    u, name: name, path: full.split("/").last,
    namespace_id: ns.id, visibility_level: 0, initialize_with_readme: false
  ).execute
  proj = res.respond_to?(:payload) ? res.payload[:project] : res
  abort "create failed: #{(proj&.errors&.full_messages || res).to_a.join(', ')}" unless proj&.persisted?
  puts "project+ created #{full} id=#{proj.id}"
else
  puts "project= exists #{full} id=#{proj.id}"
end

branch = proj.default_branch || "main"
actions = []
Find.find(dir) do |path|
  next unless File.file?(path)
  rel = path.sub(%r{^#{Regexp.escape(dir)}/?}, "")
  content = File.read(path, encoding: "UTF-8")
  blob = proj.empty_repo? ? nil : proj.repository.blob_at(branch, rel)
  if blob.nil?
    actions << { action: :create, file_path: rel, content: content }
  elsif blob.data.dup.force_encoding("UTF-8") != content
    # compare as UTF-8 bytes so non-ASCII (em-dash, arrows) doesn't false-diff
    actions << { action: :update, file_path: rel, content: content }
  end
end

if actions.any?
  svc_actions = actions.map { |a| { action: a[:action].to_s, file_path: a[:file_path], content: a[:content] } }
  result = Files::MultiService.new(
    proj, u,
    start_branch: (proj.empty_repo? ? nil : branch),
    branch_name: branch,
    commit_message: "demo: provision ci-cd + pages (ansible)",
    actions: svc_actions
  ).execute
  abort "commit failed: #{result[:message]}" unless result[:status] == :success
  puts "commit+ #{actions.map { |a| a[:file_path] }.join(', ')}"
else
  puts "commit= no changes"
end

# Deploy token for the k3s pull secret (read_registry) → CI variables the deploy job uses.
dt = proj.deploy_tokens.find_by(name: 'k3s-pull')
if dt.nil?
  dt = proj.deploy_tokens.create!(name: 'k3s-pull', read_registry: true, deploy_token_type: :project_type, expires_at: 2.years.from_now)
  { 'K8S_PULL_USER' => dt.username, 'K8S_PULL_TOKEN' => dt.token }.each do |k, v|
    var = proj.variables.find_by(key: k)
    var ? var.update!(value: v) : proj.variables.create!(key: k, value: v, masked: (k == 'K8S_PULL_TOKEN'), protected: true)
  end
  puts 'deploytoken+ k3s-pull'
else
  puts 'deploytoken= k3s-pull'
end
pd = proj.variables.find_by(key: 'PLATFORM_DOMAIN')
if pd.nil?
  proj.variables.create!(key: 'PLATFORM_DOMAIN', value: ENV['PLATFORM_DOMAIN'], protected: false); puts 'variable+ PLATFORM_DOMAIN'
elsif pd.value != ENV['PLATFORM_DOMAIN']
  pd.update!(value: ENV['PLATFORM_DOMAIN']); puts 'variable~ PLATFORM_DOMAIN'
end

puts "DEMO_DONE project=#{proj.full_path} default_branch=#{proj.default_branch || branch}"
