# Seed Harbor CI credentials as GitLab INSTANCE-level CI/CD variables so every
# pipeline can `docker login` + push to Harbor. Idempotent: writes only on diff,
# prints one line per change, ends with `changes=N` + HARBOR_CI_VARS_DONE.
# Desired state comes from $HARBOR_CI_DESIRED (JSON) so the token never touches
# disk (gitlab-rails drops to the git user, which can't read a root-0600 file);
# falls back to an ARGV file path for non-secret manual runs.
# Run via: HARBOR_CI_DESIRED='{...}' gitlab-rails runner harbor_ci_vars.rb
require "json"

src = ENV["HARBOR_CI_DESIRED"]
desired = (src && !src.empty?) ? JSON.parse(src) : JSON.parse(File.read(ARGV[0]))
changes = 0
# GitLab's maskable-value rule: >=8 chars from a restricted alphabet, no spaces.
MASKABLE = %r{\A[a-zA-Z0-9+/=@:.~-]{8,}\z}
HAS_RAW  = Ci::InstanceVariable.column_names.include?("raw")

(desired["variables"] || []).each do |v|
  key       = v["key"]
  value     = v["value"].to_s
  masked    = v.fetch("masked", false) && !(value =~ MASKABLE).nil?
  protectd  = v.fetch("protected", false)
  raw       = v.fetch("raw", false)

  var = Ci::InstanceVariable.find_by(key: key)
  if var.nil?
    attrs = { key: key, value: value, masked: masked, protected: protectd, variable_type: "env_var" }
    attrs[:raw] = raw if HAS_RAW
    Ci::InstanceVariable.create!(attrs)
    changes += 1
    puts "var+ #{key} (masked=#{masked} protected=#{protectd} raw=#{raw})"
  else
    attrs = {}
    attrs[:value]     = value    if var.value != value
    attrs[:masked]    = masked   if var.masked != masked
    attrs[:protected] = protectd if var.protected != protectd
    attrs[:raw]       = raw      if HAS_RAW && var.raw != raw
    if attrs.any?
      var.update!(attrs)
      changes += 1
      puts "var~ #{key} (#{attrs.keys.join(',')})"
    end
  end
end

puts "changes=#{changes}"
puts "HARBOR_CI_VARS_DONE"
