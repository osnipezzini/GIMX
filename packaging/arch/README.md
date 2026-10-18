# Pacote para Arch Linux

Na raiz do repositório, execute como usuário normal:

```bash
sudo pacman -S --needed base-devel git
git submodule update --init --recursive
./scripts/build-arch-package.sh --syncdeps
```

`--syncdeps` permite que o makepkg instale as dependências ausentes usando
pacman e sudo. Sem essa opção, o script apenas informa o que falta.
O pacote e os logs de trabalho ficam em `build/arch/`.
Para limitar o paralelismo, use `MAKEFLAGS=-j2 ./scripts/build-arch-package.sh`.

O script gera um PKGBUILD com versão baseada em `info.h` e no commit atual,
além de um arquivo de fontes com SHA-256. Inclui os arquivos versionados da
árvore de trabalho e dos submódulos, inclusive alterações locais; arquivos
novos precisam ser adicionados com `git add` para entrar no snapshot.
A compilação ocorre numa cópia separada, sem reutilizar os objetos locais.
Esta receita serve para empacotamento local, não para publicação direta no AUR.

Instale o arquivo `.pkg.tar.zst` indicado ao final com `sudo pacman -U CAMINHO`.
Depois execute `gimx-launcher`. As bibliotecas são instaladas em `/usr/lib`,
sem necessidade de configurar `LD_LIBRARY_PATH`.

O pacote inclui as interfaces gráficas, utilitários, traduções, bibliotecas
e firmware. Instale `avrdude` para gravar firmware com `gimx-loader`.
O utilitário Bluetooth incluído é instalado como `gimx-bdaddr`, e o launcher
usa esse nome, permitindo coexistir com o `bdaddr` do pacote `bluez-utils`.

Os executáveis são instalados com modo `0755`, sem setuid/setgid. Algumas
operações Bluetooth, USB, UHID ou de prioridade exigem permissões adicionais.
Configure o acesso aos dispositivos conforme a conexão utilizada; esse pacote
não instala regras udev nem concede capacidades automaticamente. Não é
necessário executar a interface gráfica inteira como root.

A verificação automática executa `gimx --help`; conexões reais e force feedback
precisam ser validados com hardware. O alvo inicial desta receita é `x86_64`.
