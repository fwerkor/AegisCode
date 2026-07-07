class Aegiscode < Formula
  desc "Opencode-style coding-agent CLI with subagents and governed tools"
  homepage "https://github.com/fwerkor/AegisCode"
  url "https://github.com/fwerkor/AegisCode/releases/download/v0.2.0/aegiscode-macos-x86_64"
  version "0.2.0"
  sha256 "PLACEHOLDER"

  def install
    bin.install "aegiscode-macos-x86_64" => "aegiscode"
  end

  test do
    system "#{bin}/aegiscode", "doctor"
  end
end
