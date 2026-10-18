# Repository Guidelines

## Project Structure & Module Organization

GIMX is a C/C++ gaming-device hub for GNU/Linux and Windows. `core/` contains the runtime, device connectors, haptics, and platform-specific code. The wxWidgets applications live in `config/`, `launcher/`, `fpsconfig/`, and `loader/`. Reusable libraries and Git submodules reside in `shared/`; helper programs are in `utils/`. Translations are in `po/`, firmware images in `loader/firmware/`, and GUI resources beside their applications, including `wxsmith/` layout files. Standalone diagnostic programs live in `core/test/`.

## Build, Test, and Development Commands

- `git submodule update --init --recursive`: populate dependencies before building.
- `make`: build shared libraries, utilities, applications, and Linux translations; this is also the Travis CI build command.
- `make build-core`: build the runtime and its shared-library prerequisites.
- `make clean && make DEBUG=1`: rebuild with debug symbols and, on GNU/Linux, AddressSanitizer. Clean when switching modes because compiler flags are not tracked as dependencies.
- `make clean`: remove build outputs.
- `./launcher/gimx-launcher`: start the launcher after building with the required runtime libraries available.

Use `.travis.yml` as the reference for Linux development packages, including wxWidgets, Bluetooth, libxml2, libusb, ncurses, gettext, mhash, curl, and X11 headers. Shared compiler and linker settings are in `Makedefs`.

## Coding Style & Naming Conventions

Match the surrounding file: core C commonly uses two-space indentation and braces on separate lines; C++ GUI files often use four spaces. Preserve tab-indented Makefile recipes. Use existing snake_case C names and PascalCase C++ classes, such as `SetupManager`. Preserve license headers and wxSmith-generated markers; update layout definitions alongside generated GUI changes. No repository-wide formatter or linter is configured. Builds enable `-Wall -Wextra -Werror`, so resolve warnings.

## Testing Guidelines

There is no unified test runner or enforced coverage threshold. After building prerequisites, use `make -C core/test/curses` or `make -C core/test/haptic` to build diagnostics named `curses_test` and `ff_lg_test`. Run relevant diagnostics manually and document required hardware. Verify affected GUI flows and device behavior; report platform, connection type, and sanitizer results.

## Commit & Pull Request Guidelines

Recent commits use short imperative subjects, such as “Fix compilation issues with gcc 12.2.0.” Follow that style and keep changes focused. PRs should explain the problem, resulting behavior, related issue, and validation performed. Include screenshots for GUI changes and hardware details for connector or haptic changes. Keep submodule updates intentional and identify their purpose.
