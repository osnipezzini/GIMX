#!/usr/bin/env bash
set -euo pipefail

if [[ ${1:-} == --help ]]; then
  echo "Uso: $0 [opções do makepkg]"
  echo "Gera o pacote em build/arch usando os arquivos versionados da árvore atual."
  echo "Exemplo: $0 --syncdeps"
  exit 0
fi

if (( EUID == 0 )); then
  echo "Execute como usuário normal; makepkg não deve rodar como root." >&2
  exit 1
fi

for tool in git tar sha256sum makepkg; do
  command -v "$tool" >/dev/null || { echo "Comando necessário: $tool" >&2; exit 1; }
done

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
if git submodule status --recursive | grep -Eq '^[-+U]'; then
  echo "Inicialize os submódulos nos commits registrados antes de empacotar:" >&2
  echo "  git submodule update --init --recursive" >&2
  exit 1
fi

build_dir="$repo_dir/build/arch"
mkdir -p "$build_dir"
version=$(sed -n 's/^#define INFO_VERSION "\([^"]*\)"/\1/p' info.h)
version+=".r$(git rev-list --count HEAD).g$(git rev-parse --short HEAD)"
if [[ -n $(git status --porcelain --untracked-files=no) ]]; then
  version+=".dirty"
fi

# Include tracked files from the working tree and every initialized submodule.
# Unlike git archive, this preserves local fixes inside submodules as well.
git ls-files --recurse-submodules -z > "$build_dir/source-files.list"
tar --create --gzip --file="$build_dir/gimx-src.tar.gz" \
  --transform='s,^,gimx/,' --null --verbatim-files-from \
  --files-from="$build_dir/source-files.list"
checksum=$(sha256sum "$build_dir/gimx-src.tar.gz")
checksum=${checksum%% *}
sed -e "s/@VERSION@/$version/g" -e "s/@SHA256@/$checksum/g" \
  packaging/arch/PKGBUILD.in > "$build_dir/PKGBUILD"

cd "$build_dir"
# Keep outputs local even when makepkg.conf defines global destinations.
export PKGDEST="$build_dir" SRCDEST="$build_dir" LOGDEST="$build_dir"
export BUILDDIR="$build_dir"
makepkg --cleanbuild --force "$@"
echo "Pacote(s) gerado(s):"
makepkg --packagelist
