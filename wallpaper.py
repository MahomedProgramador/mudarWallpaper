"""Muda o fundo de ecrã do Windows com fotos do Unsplash, uma por monitor.

Uso (ver MANUAL.md):
    py wallpaper.py                       tema à sorte de temas.txt (sem temas: aleatório)
    py wallpaper.py montanhas             tema escolhido só para esta vez
    py wallpaper.py --agendar 60          muda sozinho de 60 em 60 minutos
    py wallpaper.py --ao-desbloquear sim  ao desbloquear, muda se os monitores forem outros
                                          e repõe as fotos se o fundo tiver sido trocado
    py wallpaper.py --desagendar          desliga todas as mudanças automáticas
    py wallpaper.py --favorita            copia as fotos do ecrã para a subpasta favoritas
    py wallpaper.py --estado              mostra a configuração atual

Os monitores são detetados sempre que o script corre, por isso funciona com
qualquer combinação (trabalho, casa, só o portátil...). Cada monitor recebe
uma foto diferente, recortada à sua resolução exata. Sem ligação ao Unsplash,
usa fotos já guardadas com a medida de cada monitor.

Requer a variável de ambiente UNSPLASH_ACCESS_KEY com a Access Key da tua
aplicação (https://unsplash.com/oauth/applications).
"""

import argparse
import csv
import ctypes
import ctypes.wintypes as wt
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
import winreg
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

API = "https://api.unsplash.com"
PASTA_SCRIPT = Path(__file__).resolve().parent
PASTA_PADRAO = PASTA_SCRIPT / "fotos"
TEMAS = PASTA_SCRIPT / "temas.txt"
ESTADO = PASTA_SCRIPT / "monitores.json"
REGISTO = PASTA_SCRIPT / "registo.txt"
TAREFA_HORARIO = "Unsplash - mudar fundo"
TAREFA_MONITORES = "Unsplash - monitores"

TAREFA_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{descricao}</Description></RegistrationInfo>
  <Triggers>{gatilhos}</Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{sid}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec><Command>{comando}</Command><Arguments>{argumentos}</Arguments></Exec>
  </Actions>
</Task>
"""


def _guid(texto):
    return (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID(texto).bytes_le)


class FundoWindows:
    """Acesso mínimo à interface IDesktopWallpaper do Windows (fundo por monitor)."""

    def __init__(self):
        # Sem isto, com a escala do Windows a 150% as medidas vinham reduzidas
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        ctypes.oledll.ole32.CoInitialize(None)
        self._obj = ctypes.c_void_p()
        ctypes.oledll.ole32.CoCreateInstance(
            _guid("C2CF3110-460E-4fc1-B9D0-8A1C0C9CC4BD"), None, 0x17,  # CLSID_DesktopWallpaper, CLSCTX_ALL
            _guid("B92B56A9-8B55-4E14-9A89-0199BBB6F93B"), ctypes.byref(self._obj),  # IID_IDesktopWallpaper
        )
        self._vtbl = ctypes.cast(self._obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents

    def _chamar(self, indice, argtypes, *args):
        metodo = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, *argtypes)(self._vtbl[indice])
        metodo(self._obj, *args)

    def monitores(self):
        """[(id, largura, altura)] dos monitores ligados neste momento."""
        total = wt.UINT()
        self._chamar(6, [ctypes.POINTER(wt.UINT)], ctypes.byref(total))  # GetMonitorDevicePathCount
        ligados = []
        for i in range(total.value):
            caminho = ctypes.c_wchar_p()
            self._chamar(5, [wt.UINT, ctypes.POINTER(ctypes.c_wchar_p)], i, ctypes.byref(caminho))  # GetMonitorDevicePathAt
            monitor_id = caminho.value
            ctypes.windll.ole32.CoTaskMemFree(caminho)
            rect = wt.RECT()
            try:
                self._chamar(7, [wt.LPCWSTR, ctypes.POINTER(wt.RECT)], monitor_id, ctypes.byref(rect))  # GetMonitorRECT
            except OSError:
                continue  # monitor que o Windows recorda mas que não está ligado agora
            ligados.append((monitor_id, rect.right - rect.left, rect.bottom - rect.top))
        return ligados

    def atual(self, monitor_id):
        """Caminho da imagem que o Windows diz ter no monitor."""
        caminho = ctypes.c_wchar_p()
        self._chamar(4, [wt.LPCWSTR, ctypes.POINTER(ctypes.c_wchar_p)], monitor_id, ctypes.byref(caminho))  # GetWallpaper
        imagem = caminho.value
        ctypes.windll.ole32.CoTaskMemFree(caminho)
        return imagem or ""

    def preencher(self):
        self._chamar(10, [ctypes.c_int], 4)  # SetPosition(DWPOS_FILL)

    def definir(self, monitor_id, imagem):
        self._chamar(3, [wt.LPCWSTR, wt.LPCWSTR], monitor_id, str(imagem.resolve()))  # SetWallpaper


def pedir(url, chave, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Client-ID {chave}",
        "Accept-Version": "v1",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def procurar_fotos(chave, tema, orientacao, quantidade):
    params = {"orientation": orientacao, "count": min(30, max(10, quantidade)), "content_filter": "high"}
    if tema:
        params["query"] = tema
    return pedir(f"{API}/photos/random", chave, params)


def escolher_fotos(chave, tema, monitores):
    """[(id, largura, altura, foto)]: uma foto diferente para cada monitor."""
    por_orientacao = {}
    for monitor in monitores:
        _, largura, altura = monitor
        por_orientacao.setdefault("landscape" if largura >= altura else "portrait", []).append(monitor)

    escolhas = []
    for orientacao, grupo in por_orientacao.items():
        todas = procurar_fotos(chave, tema, orientacao, len(grupo))
        livres = list(todas)
        # Os monitores maiores escolhem primeiro, ficando com os originais maiores
        for monitor_id, largura, altura in sorted(grupo, key=lambda m: m[1] * m[2], reverse=True):
            if not livres:
                livres = list(todas)  # tema com poucas fotos: repete
            # Preferir fotos cujo original cobre o ecrã, para nunca haver ampliação
            boas = [f for f in livres if f["width"] >= largura and f["height"] >= altura]
            foto = boas[0] if boas else max(livres, key=lambda f: f["width"] * f["height"])
            livres.remove(foto)
            escolhas.append((monitor_id, largura, altura, foto))
    return escolhas


def ler_temas():
    try:
        linhas = TEMAS.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return []
    # Tudo o que vem depois de "#" é comentário (linhas inteiras ou traduções ao lado)
    temas = (l.split("#", 1)[0].strip() for l in linhas)
    return [t for t in temas if t]


def escolher_tema():
    """Um tema à sorte de temas.txt; sem temas, fotos aleatórias."""
    temas = ler_temas()
    return random.choice(temas) if temas else ""


def slug(texto):
    return re.sub(r"[^\w-]+", "-", texto.lower()).strip("-")


def descarregar(foto, chave, largura, altura, pasta, tema):
    # O Unsplash (imgix) devolve a foto já recortada à medida exata do ecrã
    raw = foto["urls"]["raw"]
    url = raw + ("&" if "?" in raw else "?") + urllib.parse.urlencode({
        "w": largura, "h": altura, "fit": "crop", "crop": "entropy", "q": 95, "fm": "jpg",
    })
    # Exigido pelas regras da API: conta o download para o fotógrafo
    pedir(foto["links"]["download_location"], chave)

    nome = f"{datetime.now():%Y-%m-%d_%H%M%S}_{slug(tema) or 'aleatorio'}_{largura}x{altura}_{foto['id']}.jpg"
    destino = pasta / nome
    with urllib.request.urlopen(url, timeout=60) as resp:
        destino.write_bytes(resp.read())
    return destino


def registar_creditos(pasta, ficheiro, foto):
    with open(pasta / "creditos.txt", "a", encoding="utf-8") as f:
        f.write(f"{ficheiro.name} | Foto de {foto['user']['name']} no Unsplash | {foto['links']['html']}\n")


def qualidade_maxima_jpeg():
    # Por defeito o Windows recomprime os JPEG do fundo a 85% de qualidade
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "JPEGImportQuality", 0, winreg.REG_DWORD, 100)


def ler_chave():
    """Access Key do Unsplash, guardada com setx."""
    # Lida do registo primeiro: os terminais abertos antes do setx (ex.: VS Code) não a veem
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, "UNSPLASH_ACCESS_KEY")[0]
    except FileNotFoundError:
        return os.environ.get("UNSPLASH_ACCESS_KEY", "")


def ler_ultima_mudanca():
    """{"monitores": [...], "fotos": {monitor_id: caminho}} da última mudança."""
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def guardar_ultima_mudanca(assinatura, fotos):
    ESTADO.write_text(json.dumps({
        "monitores": assinatura,
        "fotos": {monitor_id: str(ficheiro.resolve()) for monitor_id, ficheiro in fotos.items()},
    }, indent=2), encoding="utf-8")


def usar_guardadas(fundo, monitores, assinatura, pasta, motivo):
    """Sem acesso ao Unsplash: põe fotos já descarregadas com a medida exata de cada monitor."""
    candidatas = {f.name: f for f in pasta.rglob("*.jpg")}  # todas as pastas de temas e as favoritas
    usadas = {Path(fundo.atual(m)).name for m, _, _ in monitores}  # para o fundo mudar mesmo
    escolhas = []
    for monitor_id, largura, altura in monitores:
        medida = [f for nome, f in candidatas.items() if f"_{largura}x{altura}_" in nome]
        if not medida:
            # Tudo ou nada, como nas fotos novas: não fica um monitor mudado e outro não
            sys.exit(f"{motivo}. Não há fotos guardadas de {largura}x{altura} para usar em vez disso.")
        foto = random.choice([f for f in medida if f.name not in usadas] or medida)
        usadas.add(foto.name)
        escolhas.append((monitor_id, largura, altura, foto))

    print(f"{motivo}. A usar fotos já guardadas.")
    fundo.preencher()
    for monitor_id, largura, altura, ficheiro in escolhas:
        fundo.definir(monitor_id, ficheiro)
        print(f"{largura}x{altura}: {ficheiro.name}")
    guardar_ultima_mudanca(assinatura, {monitor_id: ficheiro for monitor_id, _, _, ficheiro in escolhas})


def mudar_fundo(tema, pasta, so_se_mudou):
    fundo = FundoWindows()
    monitores = fundo.monitores()
    if not monitores:
        sys.exit("Nenhum monitor ligado encontrado.")
    assinatura = sorted(list(m) for m in monitores)
    if so_se_mudou:
        ultima = ler_ultima_mudanca()
        if ultima.get("monitores") == assinatura:
            fotos = {m: Path(f) for m, f in ultima.get("fotos", {}).items()}
            if all(Path(fundo.atual(m)) == f for m, f in fotos.items()):
                print("Monitores iguais aos da última vez, nada a fazer.")
                return
            # O Windows às vezes repõe sozinho um fundo antigo: volta a pôr as últimas fotos
            if all(f.exists() for f in fotos.values()):
                for monitor_id, imagem in fotos.items():
                    fundo.definir(monitor_id, imagem)
                print("O fundo tinha sido trocado; repostas as últimas fotos.")
                return

    chave = ler_chave()
    if not chave:
        sys.exit('Falta a chave do Unsplash. Guarda-a com: setx UNSPLASH_ACCESS_KEY "a_tua_access_key"')
    pasta_tema = pasta / (slug(tema) or "aleatorio")  # uma subpasta por tema
    pasta_tema.mkdir(parents=True, exist_ok=True)

    # Descarrega tudo primeiro, para não ficar com o fundo mudado só em parte se algo falhar
    try:
        transferidas = [
            (monitor_id, largura, altura, foto, descarregar(foto, chave, largura, altura, pasta_tema, tema))
            for monitor_id, largura, altura, foto in escolher_fotos(chave, tema, monitores)
        ]
    except urllib.error.HTTPError as e:
        # Chave errada ou tema sem fotos são para corrigir, não para disfarçar com fotos antigas
        if e.code == 401:
            sys.exit("Access Key inválida.")
        if e.code == 404:
            sys.exit(f"Nenhuma foto encontrada para \"{tema}\".")
        motivo = "Limite de pedidos atingido (50 por hora em modo demo)" if e.code == 403 \
            else f"Erro {e.code} da API do Unsplash"
        usar_guardadas(fundo, monitores, assinatura, pasta, motivo)
        return
    except OSError as e:  # sem rede, tempo esgotado...
        usar_guardadas(fundo, monitores, assinatura, pasta, f"Sem ligação ao Unsplash: {getattr(e, 'reason', e)}")
        return

    qualidade_maxima_jpeg()
    fundo.preencher()
    for monitor_id, largura, altura, foto, ficheiro in transferidas:
        registar_creditos(pasta_tema, ficheiro, foto)
        fundo.definir(monitor_id, ficheiro)
        print(f"{largura}x{altura}: {ficheiro.name} (foto de {foto['user']['name']})")
    guardar_ultima_mudanca(assinatura, {monitor_id: ficheiro for monitor_id, _, _, _, ficheiro in transferidas})
    print(f"Tema: {tema or 'aleatório'}. Guardadas em {pasta_tema}")


def guardar_favorita():
    """Copia as fotos que estão no ecrã para a subpasta "favoritas", com os créditos."""
    fotos = [Path(f) for f in ler_ultima_mudanca().get("fotos", {}).values()]
    if not fotos:
        sys.exit("Ainda não há fotos no ecrã postas pelo script. Muda primeiro o fundo com: py wallpaper.py")
    for foto in fotos:
        # As fotos estão em fotos\<tema>; as favoritas ficam todas juntas em fotos\favoritas
        favoritas = foto.parent if foto.parent.name == "favoritas" else foto.parent.parent / "favoritas"
        destino = favoritas / foto.name
        if destino.exists():
            print(f"Já estava nas favoritas: {foto.name}")
            continue
        if not foto.exists():
            print(f"Já não existe (foi apagada?): {foto}")
            continue
        favoritas.mkdir(exist_ok=True)
        shutil.copy2(foto, destino)
        # Os créditos vão junto, para continuarem lá mesmo que se apaguem as fotos antigas
        creditos = foto.parent / "creditos.txt"
        linhas = creditos.read_text(encoding="utf-8").splitlines() if creditos.exists() else []
        with open(favoritas / "creditos.txt", "a", encoding="utf-8") as f:
            f.writelines(l + "\n" for l in linhas if l.startswith(f"{foto.name} |"))
        print(f"Guardada nas favoritas: {foto.name}")
    print(f"Pasta: {favoritas}")


def _sid():
    resultado = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                               capture_output=True, text=True, errors="replace", check=True)
    return resultado.stdout.strip().split(",")[-1].strip('"')


def _criar_tarefa(nome, descricao, gatilhos, sid, pasta, extra=""):
    """Cria (ou substitui) uma tarefa no Agendador de Tarefas do Windows."""
    pythonw = Path(sys.executable).with_name("pythonw.exe")  # corre sem janela de consola
    argumentos = f'"{Path(__file__).resolve()}" --pasta "{pasta}"{extra}'
    xml = TAREFA_XML.format(descricao=descricao, gatilhos=gatilhos, sid=sid,
                            comando=escape(str(pythonw)), argumentos=escape(argumentos))
    ficheiro = Path(tempfile.gettempdir()) / f"{nome}.xml"
    ficheiro.write_text(xml, encoding="utf-16")
    try:
        criada = subprocess.run(["schtasks", "/create", "/tn", nome, "/xml", str(ficheiro), "/f"],
                                capture_output=True, encoding="utf-8", errors="replace")
    finally:
        ficheiro.unlink()
    if criada.returncode:
        sys.exit(f"Não foi possível criar a tarefa \"{nome}\": {criada.stderr.strip()}")


def _apagar_tarefa(nome):
    subprocess.run(["schtasks", "/delete", "/tn", nome, "/f"], capture_output=True)


def _consultar_tarefa(nome, *opcoes):
    """Saída de schtasks /query para a tarefa, ou "" se ela não existir."""
    r = subprocess.run(["schtasks", "/query", "/tn", nome, *opcoes],
                       capture_output=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def _minutos(duracao):
    """Duração do Agendador em minutos (ex.: PT1H30M -> 90)."""
    d, h, m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?", duracao).groups(default="0")
    return int(d) * 1440 + int(h) * 60 + int(m)


def agendar(minutos, pasta):
    inicio = datetime.now().replace(microsecond=0).isoformat()
    _criar_tarefa(
        TAREFA_HORARIO, f"Muda o fundo de ecrã de {minutos} em {minutos} minutos.",
        f"<TimeTrigger><Repetition><Interval>PT{minutos}M</Interval></Repetition>"
        f"<StartBoundary>{inicio}</StartBoundary></TimeTrigger>",
        _sid(), pasta,
    )
    print(f"Mudança automática: de {minutos} em {minutos} minutos.")


def ao_desbloquear(ligar, pasta):
    if not ligar:
        _apagar_tarefa(TAREFA_MONITORES)
        print("Ao desbloquear o PC: desligado.")
        return
    sid = _sid()
    # Os 30 s dão tempo à rede para voltar depois de desbloquear
    _criar_tarefa(
        TAREFA_MONITORES, "Muda o fundo de ecrã quando os monitores ligados mudam.",
        f"<LogonTrigger><UserId>{sid}</UserId><Delay>PT30S</Delay></LogonTrigger>"
        f"<SessionStateChangeTrigger><StateChange>SessionUnlock</StateChange>"
        f"<UserId>{sid}</UserId><Delay>PT30S</Delay></SessionStateChangeTrigger>",
        sid, pasta, " --se-mudou",
    )
    print("Ao desbloquear o PC: ligado (muda se os monitores forem outros, repõe as fotos se o fundo for trocado).")


def desagendar():
    for nome in (TAREFA_HORARIO, TAREFA_MONITORES):
        _apagar_tarefa(nome)
    print("Mudanças automáticas desligadas.")


def estado():
    temas = ler_temas()
    print(f"Temas: {', '.join(temas) if temas else 'nenhum (fotos aleatórias)'}")
    xml = _consultar_tarefa(TAREFA_HORARIO, "/xml")
    if xml:
        minutos = _minutos(re.search(r"<Interval>(\w+)</Interval>", xml).group(1))
        proxima = next(csv.reader([_consultar_tarefa(TAREFA_HORARIO, "/fo", "csv", "/nh").strip()]))[1]
        print(f"Mudança automática: de {minutos} em {minutos} minutos (próxima: {proxima})")
    else:
        print("Mudança automática: desligada")
    print(f"Ao desbloquear o PC: {'ligado' if _consultar_tarefa(TAREFA_MONITORES) else 'desligado'}")
    pasta = re.search(r'--pasta "([^"]+)"', xml)
    print(f"Fotos guardadas em: {pasta.group(1) if pasta else PASTA_PADRAO}")


def main():
    parser = argparse.ArgumentParser(description="Muda o fundo de ecrã com fotos do Unsplash, uma por monitor.")
    parser.add_argument("tema", nargs="*", help="tema só para esta vez (sem tema: um à sorte de temas.txt)")
    parser.add_argument("--pasta", type=Path, default=PASTA_PADRAO,
                        help=f"onde guardar as fotos (por defeito: {PASTA_PADRAO})")
    parser.add_argument("--agendar", type=int, metavar="MINUTOS", help="mudar sozinho de MINUTOS em MINUTOS")
    parser.add_argument("--ao-desbloquear", choices=["sim", "nao", "não"],
                        help="ao desbloquear o PC, mudar se os monitores ligados forem outros "
                             "e repor as fotos se o fundo tiver sido trocado")
    parser.add_argument("--desagendar", action="store_true", help="desligar todas as mudanças automáticas")
    parser.add_argument("--favorita", action="store_true",
                        help="copiar as fotos que estão no ecrã para a subpasta favoritas")
    parser.add_argument("--estado", action="store_true", help="mostrar a configuração atual")
    parser.add_argument("--se-mudou", action="store_true",
                        help="só mudar se os monitores ligados forem outros ou se o fundo tiver sido "
                             "trocado (usado pelo agendador)")
    args = parser.parse_args()

    if args.agendar is not None and args.agendar < 1:
        parser.error("--agendar precisa de pelo menos 1 minuto")
    if args.desagendar:
        desagendar()
    if args.agendar is not None:
        agendar(args.agendar, args.pasta)
    if args.ao_desbloquear:
        ao_desbloquear(args.ao_desbloquear == "sim", args.pasta)
    if args.favorita:
        guardar_favorita()
    if args.estado:
        estado()
    if args.desagendar or args.agendar is not None or args.ao_desbloquear or args.favorita or args.estado:
        return

    if sys.stdout is None:  # a correr escondido pelo Agendador (pythonw): escreve num registo
        sys.stdout = sys.stderr = open(REGISTO, "a", encoding="utf-8")
        print(f"\n[{datetime.now():%Y-%m-%d %H:%M}]")
    mudar_fundo(" ".join(args.tema) or escolher_tema(), args.pasta, args.se_mudou)


if __name__ == "__main__":
    main()
