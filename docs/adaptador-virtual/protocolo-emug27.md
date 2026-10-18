# Especificação observada do EMUG27

Este documento distingue **observado** (código consultado), **proposto** (novo
comportamento) e **a validar** (depende de execução/captura). Referências e
commits estão no [índice](README.md). A fonte do firmware é externa a este repo.

## 1. Camadas e responsabilidades

```text
Físicos → gimxinput → configuração XML → estado de eixos/botões
                                      → construtor de relatório G27
                                      → adaptador → host USB → driver → jogo

Jogo → driver → USB OUT → adaptador → haptic_source_lg
     → haptic_core/tweaks → haptic_sink → dispositivo físico
```

CP2102: ponte USB/UART do lado do processo GIMX. Pro Micro/ATmega32U4: firmware
que apresenta o dispositivo G27 ao outro lado USB. O driver roda no sistema
operacional; a placa responde às requisições dele, não o transmite.

## 2. Versões: identidade comum não implica comportamento idêntico

| Propriedade | Legado v5.8 (`EMUG27PS3`) | Snapshot atual (`EMUG27`) |
|---|---|---|
| ID do tipo no protocolo | `0x08` | `0x08` |
| VID:PID | `046d:c29b` | Igual |
| `bcdDevice` | `0x1238` | Igual |
| Descritor de relatórios HID | 108 bytes | 133 bytes |
| Entrada/saída/feature declarados | 11 / 7 / 144 bytes | Iguais |
| Botões descritos na página Button | 19 | 22 + 1 em outro campo |
| Consulta explícita VERSION | Não tratada em `handle_packet()` | Resposta major=8, minor=0 |
| Ajuste de baudrate | 500.000 fixo no código | Comando BAUDRATE; inicial 500.000 |
| Recepção serial parcial | Leitura bloqueante na interrupção | Timeout de recepção com reset |
| SET_IDLE de classe | Não tratado no handler consultado | Tratado |

**Importante:** o host GIMX tenta `BYTE_VERSION`. Se a leitura falha ou o
comprimento difere de dois, imprime 5.8 como fallback. Não usar esse log para
identificar definitivamente a placa ou selecionar o descritor virtual.

Proposta: dois perfis imutáveis de referência (`legacy-v5.8` e
`current-source-8.0`), com escolha explícita nos testes. O perfil padrão de
distribuição só será fixado depois de confrontar driver e capturas. Não misturar
descritor legado com respostas do firmware atual sem registrar uma divergência.

## 3. Identidade e topologia USB observadas

| Campo | Valor |
|---|---|
| USB | 2.00, operação full-speed no firmware AVR |
| Device class/subclass/protocol | `00/00/00` |
| EP0 max packet | 16 bytes no alvo AVR8 |
| Configurações / interfaces | 1 / 1 |
| Interface | 0, alternate setting 0, HID `03/00/00` |
| HID version / country | `0x0111` / `0x21` |
| Interrupt IN | endereço `0x81`, max packet 16, intervalo 2 ms |
| Interrupt OUT | endereço `0x02`, max packet 16, intervalo 2 ms |
| Produto | string índice 2: `G27 Racing Wheel` |
| Fabricante / serial | sem descritor |
| Idioma | inglês (`LANGUAGE_ID_ENG` da LUFA) |
| Alimentação anunciada | bus-powered, 98 mA |

Não confundir: tamanho do endpoint (16), relatório IN útil (11), OUT HID (7),
feature declarado (144), limite do buffer de controle no firmware (64), período
de polling USB (2 ms) e período de envio do GIMX (padrão 10 ms, mínimo 1 ms).
São limites/camadas diferentes. Sem evidência, não preencher o IN até 16 bytes.

## 4. Relatório de entrada construído pelo GIMX

Fonte local: `shared/gimxcontroller/include/g27_ps3.h` e
`shared/gimxcontroller/src/g27_ps3.c`. Payload de 11 bytes, sem Report ID no
descritor. Campos multibyte são serializados conforme o layout observado no
host little-endian atual; implementação nova deve codificar bytes explicitamente.

| Offset em bytes | Campo | Interpretação |
|---|---|---|
| 0 | `hatAndButtons` | Hat no nibble baixo; quatro botões no alto |
| 1–2 | `buttons` | Word de botões, byte menos significativo primeiro |
| 3–4 | `buttonsAndWheel` | Direção nos 14 bits altos; L4/L5 nos dois baixos |
| 5 | `gasPedal` | 8 bits |
| 6 | `brakePedal` | 8 bits |
| 7 | `clutchPedal` | 8 bits |
| 8–10 | `shifter.x/y/b` | Codificação adicional do câmbio |

Direção: `clamp(axis + 8192, 0, 16383) << 2`, combinada com os dois botões.
Pedais: o estado neutro inicial é 255. Hat neutro: 8; oito direções: 0–7.
Estado inicial do câmbio: `80 80 9c` hexadecimal. Relatório inicial derivado do
construtor local: `08 00 00 00 80 ff ff ff 80 80 9c`.

O XML oferece direção, três pedais, hat, botões e marchas 1–6/R. O firmware
legado nomeia parte dos bits como vendor-specific; o descritor atual expõe mais
deles como botões. Portanto a quantidade apresentada pelo driver/jogo não deve
ser inferida apenas do número de entradas do XML.

O JSON de evidências registra os offsets em bits dos campos HID das duas
versões. A posição dos campos de entrada permanece compatível no total de
88 bits; sua semântica HID mudou. O comentário legado sobre endianness da
direção não substitui a verificação byte a byte do construtor e das capturas.

## 5. Enquadramento serial e protocolo de gerenciamento

Pacote: `[tipo:u8][comprimento:u8][payload:comprimento]`. O host define espaço
de 254 bytes de payload, mas isso **não** autoriza enviar esse tamanho ao
firmware: seus buffers de IN e controle são menores. Não há CRC ou número de
sequência nesse enquadramento. Um transporte por stream precisa acumular
fragmentos, validar comprimento e separar múltiplos pacotes recebidos juntos.
Os opcodes e exemplos de bytes da tabela abaixo estão em hexadecimal.

| Opcode | Direção/semântica observada |
|---|---|
| `11` TYPE | Host consulta sem payload; resposta `11 01 08` para G27 |
| `22` STATUS | Legado responde `started`; snapshot atual responde estado de spoof; não usar como contrato portátil de conexão |
| `33` START | Resposta de um byte; depois firmware libera inicialização USB |
| `44` CONTROL_DATA | Transporte genérico de controles em perfis que usam forwarding; não supor que EMUG27 use toda essa capacidade |
| `55` RESET | Reset físico por watchdog; o host envia sem esperar a mesma resposta de TYPE |
| `66` IDS | Snapshot atual recebe VID/PID em quatro bytes; descritor EMUG27 continua com IDs fixos |
| `77` VERSION | Atual responde `77 02 08 00`; legado não implementa a consulta |
| `88` BAUDRATE | Atual consulta/ajusta baudrate em unidades de 100.000; não pertence ao perfil legado |
| `99` DEBUG | Diagnóstico firmware → GIMX, não confundir com efeito |
| `ee` OUT_REPORT | Firmware → GIMX, dados recebidos pelo endpoint OUT |
| `ff` IN_REPORT | GIMX → firmware, relatório a disponibilizar no IN; sem ACK dedicado |

Fluxo observado no host:

1. Abrir a porta inicialmente a 500.000 baud.
2. Consultar TYPE e validar o perfil esperado.
3. Consultar VERSION, admitindo o fallback legado.
4. Enviar RESET e aguardar reinicialização.
5. Para major >= 8, consultar/negociar baudrate entre os candidatos do host.
6. Preparar relatório e destino de haptics; G27 não exige controle passthrough.
7. Enviar START, registrar callbacks e entrar no loop.
8. Enviar IN_REPORT e processar OUT_REPORT em sentido inverso.

Fonte local: `core/controller.c`, especialmente `adapter_detect()`,
`adapter_get_version()`, `adapter_start()`, `adapter_process_packet()` e
`adapter_send()`. A saída virtual pode chamar operações equivalentes diretamente,
sem simular o tempo gasto na serial ou inventar uma porta `/dev/ttyUSB*`.

## 6. Requisições USB e os limites da referência

Descritores padrão de device/configuration/string/HID/report são fornecidos
pelo firmware e pela LUFA. O novo backend precisa atender também seleção de
configuração e semântica de transferências control/interrupt, inclusive erros,
cancelamento e desconexão; copiar apenas o array `Report[]` é insuficiente.

Nos handlers de EMUG27 consultados:

- GET_REPORT (`01`): gera diagnóstico, sem implementar um banco completo de
  feature reports. O handler legado restringe o diagnóstico a features; o atual
  registra tipo e ID. Não há implementação completa de resposta de 144 bytes.
- SET_REPORT (`09`): recebe dados de controle e confirma a fase correspondente;
  features produzem diagnóstico. Isso não é o mesmo que encaminhar o payload
  ao haptic core pelo endpoint interrupt OUT.
- SET_IDLE (`0a`): explicitamente tratado no snapshot atual; não no handler legado.

**A validar:** resultado USB efetivo de requisições não consumidas pelo handler,
comportamento da LUFA, STALL/timeout, SET/GET_PROTOCOL, tamanhos parciais e
reset/suspensão. Não inferir ACK, STALL ou resposta zero apenas pela ausência
de um case. Esses resultados precisam de captura ou emulação de referência.

O feature de 144 bytes declarado no HID não significa que exista uma API
funcional desse tamanho no firmware. O buffer de controle tem 64 bytes; a
emulação deve validar comprimentos sem reproduzir acessos fora de limites.
Decisões para pedidos inválidos devem ser documentadas como endurecimento,
não anunciadas como comportamento já observado na placa.

## 7. Force feedback: o que já existe

Fonte local: `core/haptic/source/haptic_source_lg.c`,
`core/haptic/common/ff_lg.[ch]`, `core/haptic/haptic_core.[ch]` e sinks.

O relatório Logitech clássico tem 7 bytes; há quatro slots. O byte inicial
combina máscara de slots e opcode, exceto o comando estendido `f8`.

| Categoria | Comportamento observado no GIMX |
|---|---|
| Download / download-and-play / play / stop / refresh | Atualização e execução de slots |
| Força constante | Conversão para nível assinado interno |
| Spring / damper | Conversão de condições, inclusive variantes de alta resolução |
| Força variável | Conversão limitada; certas variantes não são convertíveis para constante |
| Range 200/900 e range explícito | Convertidos para evento interno RANGE |
| RPM LEDs | Convertidos para evento interno LEDS |
| Mudança de identidade/modo | Explicitamente ignorada pelo parser de haptics em certos comandos |
| Outros tipos/opcodes definidos em headers | Nem todos são implementados; há avisos de unsupported |

**A saída física importa:** o sink `haptic_sink_os`, visto no log do usuário,
encaminha constante/spring/damper. Para RANGE ele imprime uma orientação; LEDS
e RUMBLE não são encaminhados nesse switch. Logo não prometer ajuste automático
de rotação ou LEDs no OpenFFBoard apenas porque o parser os reconhece.

Equivalência mínima: preservar os efeitos que o caminho físico atual realmente
converte e respeitar seus limites. Expansões ficam em itens separados. O fato
de o kernel anunciar determinado conjunto de efeitos também depende do driver
Logitech efetivamente carregado, não só desse parser.

## 8. Estado proposto para a emulação

```text
CREATED → READY → ENUMERATING → CONFIGURED → RUNNING
             ↖ RESETTING ←────────────────────┘
qualquer estado → DISCONNECTED / FAILED → CLOSED
```

São estados novos de organização interna; não nomes de estados da LUFA.
TYPE/versão identificam o perfil antes da publicação; START permite publicar;
RESET limpa filas, relatórios e efeitos, e reproduz a desconexão/reenumeração
esperada pelo perfil. Pausa/suspensão do host não deve ser confundida com erro
de serial. STOP local encerra efeitos e remove o dispositivo, de forma idempotente.

A implementação precisa preservar ordem de comandos, distinguir resposta de
controle de evento OUT e nunca responder duas vezes à mesma transferência.
Comandos não suportados devem gerar diagnóstico explícito e resposta USB
definida após estudo da referência, sem travar o processo.
