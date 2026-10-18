# Adaptador GIMX virtual — levantamento e plano

Data: 18/10/2026. Estado: **pesquisa e planejamento; adaptador virtual ainda não implementado**.

## Objetivo acordado

Substituir o conjunto CP2102 + Pro Micro pelo equivalente virtual do adaptador
EMUG27 no próprio computador, primeiro Linux/Proton, com arquitetura e prova de
viabilidade Windows previstas desde o início. Preservar o config, os XML,
mapeamentos e o caminho bidirecional de force feedback. Um joystick genérico
que apenas tenha eixos parecidos **não satisfaz** o objetivo.

Não há pergunta bloqueante para este levantamento. Jogos prioritários, versão
do Proton e versão/pacote do driver Logitech Windows continuam necessários
para a futura homologação, sem impedir o trabalho de especificação agora.

## Documentos

1. [Especificação observada do adaptador](protocolo-emug27.md): versões,
   descritores, relatórios, serial, inicialização e limites do force feedback.
2. [Arquitetura Linux e Windows](arquitetura.md): comparação de mecanismos,
   interfaces propostas, integração ao GIMX e decisões condicionais.
3. [Execução, testes e esforço](plano-validacao.md): entregas, critérios de
   aprovação, riscos, estimativas e lista de tarefas.
4. [Evidência extraída dos descritores](evidencias-descritores.json): bytes,
   hashes, campos e tamanhos de duas revisões oficiais.

## Conclusões principais

- O adaptador implementa um dispositivo USB HID G27 e transporta dados e comandos
  entre o host USB e o GIMX. Ele não envia um driver ao computador.
- A equivalência exige preservar descritores, relatórios, respostas de controle,
  tratamento de endpoints, estado e retorno de força; VID/PID sozinho não basta.
- **USB virtual completo é a linha principal de investigação**: Linux com
  USB/IP + VHCI em loopback, Windows com UDE/UdeCx. São propostas, não soluções
  já homologadas neste projeto.
- UHID e uinput não são escolhidos como substituição equivalente. O driver
  `hid-lg` do Linux v6.12 verifica `hid_is_usb()` e obtém a interface USB do pai;
  `hid-lg4ff` consulta o descritor USB. Declarar `BUS_USB` em UHID não fabrica
  essa hierarquia. Logo, a biblioteca UHID existente não resolve essa exigência.
- O Windows precisará de uma implementação própria de USB virtual e instalação
  de driver. Não basta recompilar uma implementação Linux nem mudar o VID/PID
  de um dispositivo VHF.
- A mensagem **“Firmware version: 5.8” não comprova a versão instalada**:
  `adapter_get_version()` usa 5.8 como fallback se não obtiver a resposta de dois
  bytes. Isso explica por que o erro de leitura pode aparecer antes dessa mensagem.
- As versões legada e atual diferem no descritor HID, apesar de manterem
  identidade USB e tamanhos de relatórios. Precisamos de perfis versionados.
- Equivalência inclui os limites reais da tradução de efeitos do GIMX; ela não
  significa implementar todos os efeitos de um G27 físico original.

## Escopo e fronteiras

Incluído: controles completos do perfil G27, retorno de força, integração ao
config/launcher, diagnósticos, instalação Arch e planejamento de distribuição
Windows. Manter C/C++; esta iniciativa não retoma a migração para Rust.

Fora do primeiro ciclo: outros perfis de console, autenticação PS4/Xbox, conexão
USB física a outro computador, novos recursos de firmware e compatibilidade
universal com todos os jogos. Essas exclusões não reduzem o perfil EMUG27.

O dispositivo virtual deve se apresentar no sistema de destino como G27
equivalente. A serial física e seus 500 kbaud são detalhes substituíveis de
transporte, não um limite de velocidade a reproduzir. O protocolo serial pode
ser mantido como interface de compatibilidade ou fixture de testes.

## Fontes e rastreabilidade

| Fonte | Revisão consultada | Utilização |
|---|---|---|
| GIMX deste checkout | `5731507e2a7a57ce2300ac41afd3a97e993d3b70` | Construção G27, inicialização, protocolo e haptics |
| GIMX-firmwares legado | `fd02ed3e3c4a620a4c3a49deb63a793ead454195` (`v5.8`) | `EMUG27PS3`, referência legada |
| GIMX-firmwares atual consultado | `ab2215ebad5d50fd25b6b40ac74254f1f4c0bda5` | `EMUG27` e `adapter_common.c`, versão interna 8.0 |
| Linux | tag `v6.12`, `hid-lg.c` e `hid-lg4ff.c` | Dependência do transporte USB e driver Logitech |
| Linux/Microsoft | documentação oficial consultada em 18/10/2026 | UHID, USB/IP, Raw Gadget, VHF, UDE e assinatura |

O snapshot de código atual do firmware não deve ser chamado de tag v8.0: seu
commit é explicitamente o da tabela. O código dos submódulos foi inspecionado
nos commits registrados pelo checkout; não se presume que o upstream seja idêntico.

Links externos principais:

- [Firmware legado](https://github.com/matlo/GIMX-firmwares/tree/fd02ed3e3c4a620a4c3a49deb63a793ead454195/EMUG27PS3).
- [Firmware atual consultado](https://github.com/matlo/GIMX-firmwares/tree/ab2215ebad5d50fd25b6b40ac74254f1f4c0bda5/EMUG27).
- [Código comum do firmware](https://github.com/matlo/GIMX-firmwares/blob/ab2215ebad5d50fd25b6b40ac74254f1f4c0bda5/adapter_common.c).
- [Driver Logitech Linux](https://github.com/torvalds/linux/blob/v6.12/drivers/hid/hid-lg.c)
  e [force feedback](https://github.com/torvalds/linux/blob/v6.12/drivers/hid/hid-lg4ff.c).

## Reproduzir a evidência dos descritores

```bash
git clone https://github.com/matlo/GIMX-firmwares.git /tmp/gimx-firmware-reference
python3 scripts/audit-emug27.py /tmp/gimx-firmware-reference \
  --output /tmp/evidencias-descritores.json
diff -u docs/adaptador-virtual/evidencias-descritores.json \
  /tmp/evidencias-descritores.json
```

O script lê os dois commits fixados via `git show`, remove comentários do array
`Report[]` e calcula campos/tamanhos e SHA-256. Não usa o firmware para programar
placas, não cria dispositivos e não modifica o clone. Seu parser é limitado aos
itens HID presentes nessas duas fontes; não é um parser HID de uso geral.

## O que foi e não foi verificado

Verificado por leitura de código, extração reproduzível e documentação oficial.
Nenhum driver novo foi carregado, firmware atualizado ou dispositivo virtual
criado. Não foram executados testes de jogos, Proton, force feedback ou Windows.
Capturas USB e provas de execução continuam tarefas do plano, não resultados
implícitos deste levantamento. Nenhuma alteração foi feita nos XML do usuário.
