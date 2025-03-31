{pkgs}: {
  deps = [
    pkgs.playwright-driver
    pkgs.gitFull
    pkgs.postgresql
    pkgs.openssl
  ];
}
