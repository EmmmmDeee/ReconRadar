{pkgs}: {
  deps = [
    pkgs.libxcrypt
    pkgs.playwright-driver
    pkgs.gitFull
    pkgs.postgresql
    pkgs.openssl
  ];
}
