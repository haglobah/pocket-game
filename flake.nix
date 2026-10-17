{
  description = "A project by ?.";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    pyxel.url = "github:haglobah/pyxel";
    pyxel.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    inputs@{
      flake-parts,
      self,
      ...
    }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
      ];
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
        "x86_64-darwin"
      ];
      perSystem =
        {
          config,
          self',
          inputs',
          pkgs,
          system,
          ...
        }:
        {
          _module.args.pkgs = import self.inputs.nixpkgs {
            inherit system;
            config.allowUnfree = true;
          };
          # Per-system attributes can be defined here. The self' and inputs'
          # module parameters provide easy access to attributes of the same
          # system.

          # Equivalent to  inputs'.nixpkgs.legacyPackages.hello;
          packages.default = pkgs.hello;
          devShells.default = pkgs.mkShell {
            packages = with pkgs; [
              nixfmt
              just
              # inputs'.pyxel.packages.default
              ruff
              ffmpeg
              uv
              python313 # .venv base; must share glibc with /run/opengl-driver
              ninja
              pkg-config
              alsa-lib
              libjack2
              libGL
              # (python3.withPackages (pp: [
              #   pp.ninja
              #   # pp.arcade # for example
              # ]))
            ];
            shellHook = ''
              export NINJA=$(which ninja)
              # The SDL inside the pyxel wheel dlopens these at runtime.
              # /run/opengl-driver/lib holds the NixOS GPU driver behind libGL.
              export LD_LIBRARY_PATH=${
                pkgs.lib.makeLibraryPath (
                  with pkgs;
                  [
                    libGL
                    alsa-lib
                    libpulseaudio
                    pipewire
                    wayland
                    libxkbcommon
                    libdecor
                    libx11
                    libxcursor
                    libxrandr
                    libxi
                    libxext
                  ]
                )
              }:/run/opengl-driver/lib:$LD_LIBRARY_PATH
            '';
          };
        };
      flake = {
        # The usual flake attributes can be defined here, including system-
        # agnostic ones like nixosModule and system-enumerating ones, although
        # those are more easily expressed in perSystem.
      };
    };
}
