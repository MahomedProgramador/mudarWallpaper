# Manual: fundo de ecrã com fotos do Unsplash

O `wallpaper.py` põe uma foto do Unsplash diferente em cada monitor, recortada à medida exata do ecrã para ficar nítida.

Depois de ligado, trata de tudo sozinho:

- **Muda o fundo de X em X minutos**, com um tema à sorte da tua lista.
- **Ajusta-se aos monitores:** quando chegas a casa e ligas outros monitores, põe fotos novas à medida deles.
- **Funciona sem internet:** se não conseguir ir ao Unsplash, usa fotos que já tem guardadas.

## Antes de começar

Os comandos correm num terminal aberto na pasta do projeto:

```
cd D:\mudarWallpaper
```

No terminal do VS Code (PowerShell) basta isto. Na Linha de Comandos (cmd), usa `cd /d D:\mudarWallpaper`.

## Resumo rápido

**No dia a dia**

| Quero... | Comando |
|---|---|
| Mudar o fundo agora | `py wallpaper.py` |
| Mudar agora, com um tema só desta vez | `py wallpaper.py lisbon` |
| Guardar as fotos do ecrã nas favoritas | `py wallpaper.py --favorita` |
| Ver a configuração atual | `py wallpaper.py --estado` |

**Configurar**

| Quero... | Comando |
|---|---|
| Escolher os temas automáticos | Editar o ficheiro `temas.txt` |
| Mudar o intervalo (ex.: 30 minutos) | `py wallpaper.py --agendar 30` |
| Ligar a mudança ao desbloquear o PC | `py wallpaper.py --ao-desbloquear sim` |
| Desligar a mudança ao desbloquear o PC | `py wallpaper.py --ao-desbloquear nao` |
| Parar todas as mudanças automáticas | `py wallpaper.py --desagendar` |
| Voltar a ligar tudo | `py wallpaper.py --agendar 60 --ao-desbloquear sim` |
| Ver a ajuda do script | `py wallpaper.py --help` |

Podes juntar várias opções no mesmo comando, por exemplo `py wallpaper.py --agendar 120 --estado`.

---

## Mudar o fundo agora

| Comando | O que faz |
|---|---|
| `py wallpaper.py` | Usa um tema à sorte do `temas.txt` |
| `py wallpaper.py mountains` | Usa o tema `mountains`, só desta vez |
| `py wallpaper.py "beach sunset"` | Temas com espaços levam aspas |

O tema escrito no comando não altera o `temas.txt`. Também é a melhor forma de experimentar um tema antes de o acrescentar à lista.

> **Escreve os temas em inglês.** O Unsplash encontra muito mais fotos: `mountains` dá mais de 10.000, `montanhas` só 61.

## Escolher os temas

Os temas das mudanças automáticas estão no `temas.txt`. São mais de 150, organizados por categorias (natureza, mar, céu e espaço, cidades, Portugal, viagens, animais, abstrato...), cada um com a tradução ao lado.

Um tema está **ativo** quando a linha não começa por `#`:

```
mountains                      # montanhas       <- ativo
# northern lights              # aurora boreal   <- desativado
```

- **Ativar:** apaga o `# ` do início da linha.
- **Desativar:** volta a pôr o `# ` no início.
- **Não apagues o `#` antes da tradução.** Tudo o que vem depois dele é ignorado. Sem ele, o script pesquisava "mountains montanhas" e encontrava poucas fotos.

Em cada mudança, o script escolhe à sorte um dos temas ativos:

| Quero... | No `temas.txt` |
|---|---|
| Vários temas, um à sorte | Vários temas ativos |
| Sempre o mesmo tema | Só um tema ativo |
| Fotos totalmente aleatórias | Nenhum tema ativo |

Podes acrescentar temas teus em qualquer sítio do ficheiro. Basta guardar: a alteração conta na mudança seguinte. Para confirmar quais estão ativos, corre `py wallpaper.py --estado`.

## Guardar fotos favoritas

Gostaste das fotos que estão no ecrã? Corre:

```
py wallpaper.py --favorita
```

As fotos que estão nos monitores são copiadas para `fotos\favoritas`, com o autor e o link de cada uma.

- **Com vários monitores, guarda a foto de cada um.** Se só gostas de uma, apaga a outra da pasta `favoritas`. A resolução no nome diz de que monitor é (por exemplo, `_2560x1080_`).
- **As favoritas são cópias.** Podes apagar fotos antigas, ou pastas de temas inteiras, à vontade, que as favoritas ficam.
- **As favoritas de todos os temas ficam juntas** na mesma pasta. O tema está no nome de cada foto.
- **Quando não há internet, as favoritas também entram** nas fotos que o script pode usar (ver [Sem internet](#sem-internet)).

## Mudanças automáticas

Há duas mudanças automáticas, independentes uma da outra. Podes ter as duas ligadas, só uma ou nenhuma.

### De X em X minutos

```
py wallpaper.py --agendar MINUTOS
```

| Intervalo | Comando |
|---|---|
| 30 minutos | `py wallpaper.py --agendar 30` |
| 1 hora | `py wallpaper.py --agendar 60` |
| 2 horas | `py wallpaper.py --agendar 120` |
| 1 vez por dia | `py wallpaper.py --agendar 1440` |

- O intervalo conta a partir do momento em que corres o comando. Com `--agendar 60` às 16:44, as mudanças são às 17:44, 18:44, e assim por diante.
- Se o PC estiver desligado ou em suspensão à hora marcada, a mudança é feita assim que voltar.
- **Não uses menos de 10 minutos.** No modo gratuito, o Unsplash permite 50 pedidos por hora. Cada mudança gasta cerca de 3 pedidos com 2 monitores, ou 5 com 4 monitores.

### Ao desbloquear o PC

| Quero... | Comando |
|---|---|
| Ligar | `py wallpaper.py --ao-desbloquear sim` |
| Desligar | `py wallpaper.py --ao-desbloquear nao` |

Quando inicias sessão ou desbloqueias o PC, o script espera 30 segundos e compara os monitores ligados com os da última mudança:

| Situação | O que faz |
|---|---|
| Os mesmos monitores (ex.: voltas de uma pausa) | Nada |
| Outros monitores (ex.: chegas a casa e ligas os teus) | Põe fotos novas à medida de cada um |
| O Windows trocou o fundo por um antigo | Volta a pôr as últimas fotos, sem gastar pedidos ao Unsplash |

> Se ligares monitores sem bloquear e desbloquear o PC, as fotos só se ajustam na mudança seguinte. Para ajustar logo, corre `py wallpaper.py`.

### Parar e voltar a ligar

| Quero... | Comando |
|---|---|
| Parar as duas | `py wallpaper.py --desagendar` |
| Voltar a ligar as duas | `py wallpaper.py --agendar 60 --ao-desbloquear sim` |

Ao parar, o fundo atual fica como está e as fotos guardadas não são apagadas.

## Sem internet

Quando não consegue fotos novas, o script usa fotos que já tem guardadas, de todas as pastas de temas e das favoritas. Isto acontece:

- sem ligação à internet;
- com o limite de 50 pedidos por hora atingido;
- com o Unsplash em baixo.

Cada monitor recebe uma foto guardada com a sua medida exata e, sempre que possível, diferente da que está no ecrã. Se não houver nenhuma com a medida de algum monitor (por exemplo, um monitor que nunca teve fotos), não muda nada. Em qualquer dos casos, o motivo fica escrito no `registo.txt`.

Uma Access Key errada ou um tema sem resultados não usam as fotos guardadas: o script mostra o erro, para o poderes corrigir.

## Ver a configuração atual

```
py wallpaper.py --estado
```

O resultado é parecido com isto:

```
Temas: nature, mountains, beach
Mudança automática: de 60 em 60 minutos (próxima: 23/10/2026 17:44:22)
Ao desbloquear o PC: ligado
Fotos guardadas em: D:\mudarWallpaper\fotos
```

Os temas aparecem em inglês, porque é assim que o script os pesquisa.

## Onde ficam as coisas

Tudo fica na pasta `D:\mudarWallpaper`:

| Ficheiro | Para que serve |
|---|---|
| `wallpaper.py` | O script |
| `temas.txt` | Os temas das mudanças automáticas |
| `MANUAL.md` | Este manual |
| `fotos\<tema>\*.jpg` | As fotos descarregadas, numa pasta por tema, com o tema e a resolução no nome |
| `fotos\<tema>\creditos.txt` | O autor e o link de cada foto desse tema |
| `fotos\favoritas\` | As fotos guardadas com `--favorita`, com os créditos |
| `registo.txt` | O que aconteceu em cada mudança automática, incluindo erros. Pode ser apagado. |
| `monitores.json` | Os monitores e as fotos da última mudança. Se o apagares, o próximo desbloqueio descarrega fotos novas. |

**Cada tema tem a sua pasta**, com o nome do tema como é pesquisado: `ocean waves` fica em `fotos\ocean-waves`. As fotos sem tema (nenhum tema ativo) ficam em `fotos\aleatorio`.

**As fotos vão-se acumulando:** cerca de 35 MB por dia, com 2 monitores e uma mudança por hora. Podes apagar as antigas, ou a pasta inteira de um tema de que não gostaste, à vontade, mas deixa algumas de cada monitor para quando não houver internet.

### Usar outra pasta para as fotos

Indica a pasta nas duas mudanças automáticas ao mesmo tempo, porque cada uma guarda a sua:

```
py wallpaper.py --agendar 60 --ao-desbloquear sim --pasta "D:\Fundos"
```

Para uma mudança manual, usa `py wallpaper.py --pasta "D:\Fundos"`. As favoritas passam a ficar em `D:\Fundos\favoritas`.

## Chave do Unsplash

A chave está guardada na variável de ambiente `UNSPLASH_ACCESS_KEY`. Para a trocar:

```
setx UNSPLASH_ACCESS_KEY "nova_access_key"
```

Usa a **Access Key**, não a Secret Key. A chave nova conta logo, em qualquer terminal. Podes gerir a aplicação em https://unsplash.com/oauth/applications.

## Problemas comuns

| Mensagem ou sintoma | O que fazer |
|---|---|
| O fundo não muda sozinho | Corre `py wallpaper.py --estado` para ver se está ligado. Depois abre o `registo.txt` e vê a última mensagem. |
| "Access Key inválida" | Volta a correr o `setx` com a Access Key certa. |
| "Falta a chave do Unsplash" | Corre o `setx` (ver [Chave do Unsplash](#chave-do-unsplash)). |
| "Nenhuma foto encontrada para ..." | O tema é demasiado específico ou está em português. Simplifica-o ou escreve-o em inglês. |
| "Limite de pedidos atingido" | Até passar uma hora, o script usa fotos guardadas. Se acontecer muitas vezes, aumenta o intervalo. |
| "Não há fotos guardadas de ..." | Não havia internet nem fotos guardadas com a medida desse monitor. Quando houver internet, corre `py wallpaper.py`. |
| Deixou de mudar depois de atualizar o Python | As tarefas apontam para a versão antiga. Corre `py wallpaper.py --agendar 60 --ao-desbloquear sim`. |
| Um monitor ficou com a foto errada ou esticada | Corre `py wallpaper.py` para pôr fotos à medida dos monitores ligados agora. |
| O fundo voltou a uma imagem antiga | É o Windows a repor um fundo antigo. Bloqueia e desbloqueia o PC (Windows+L): passados 30 segundos, as fotos voltam. |

As mudanças automáticas são tarefas do Agendador de Tarefas do Windows, chamadas "Unsplash - mudar fundo" e "Unsplash - monitores". Não precisas de mexer lá, porque os comandos acima tratam de tudo.

## Instalar noutro PC

1. Instala o Python a partir de https://www.python.org (Windows 10 ou 11). Não é preciso instalar mais nada.
2. Copia a pasta `mudarWallpaper` para o novo PC. Bastam o `wallpaper.py`, o `temas.txt` e este manual.
3. Cria uma aplicação em https://unsplash.com/oauth/applications e copia a **Access Key**.
4. Guarda a chave: `setx UNSPLASH_ACCESS_KEY "a_tua_access_key"`
5. Abre um terminal na pasta e experimenta: `py wallpaper.py`
6. Liga as mudanças automáticas: `py wallpaper.py --agendar 60 --ao-desbloquear sim`

Se puseres a pasta noutro sítio, os comandos correm nessa pasta e as fotos ficam na subpasta `fotos` dela.
