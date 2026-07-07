$ErrorActionPreference = 'Stop'
$url64 = 'https://github.com/fwerkor/AegisCode/releases/download/v0.5.0/aegiscode-windows-x86_64.exe'
$packageArgs = @{
  packageName   = 'aegiscode'
  fileType      = 'exe'
  url64bit      = $url64
  softwareName  = 'AegisCode'
  checksum64    = 'PLACEHOLDER'
  checksumType64= 'sha256'
  silentArgs    = ''
  validExitCodes= @(0)
}
Install-ChocolateyPackage @packageArgs
