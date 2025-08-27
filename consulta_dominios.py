import tkinter as tk
from tkinter import ttk
import threading
import time
import requests
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime

# ================================
# Funções de consulta
# ================================

def formatar_data_br(data_iso):
    if not data_iso:
        return ""
    try:
        dt = datetime.fromisoformat(data_iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except:
        return data_iso

def consultar_br(domain):
    info = {
        "Dominio": domain,
        "Origem": "Registro.br",
        "Expiração": "",
        "Servidor DNS": "",
        "Disponibilidade": "",
        "Dono/Entidade": ""
    }
    try:
        url = f"https://rdap.registro.br/domain/{domain}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            info["Disponibilidade"] = "Domínio disponível"
            return info
        resp.raise_for_status()
        data = resp.json()
        info["Disponibilidade"] = "Registrado"

        # Expiração
        for ev in data.get("events", []):
            if ev.get("eventAction", "").lower() == "expiration":
                info["Expiração"] = formatar_data_br(ev.get("eventDate"))
                break

        # Servidores DNS
        ns_list = [ns.get("ldhName") for ns in data.get("nameservers", []) if ns.get("ldhName")]
        info["Servidor DNS"] = ", ".join(ns_list)

        # Dono/Entidade via RDAP
        entities = data.get("entities", [])
        donos = [ent.get("handle", "Desconhecido") for ent in entities if ent.get("roles")]
        info["Dono/Entidade"] = ", ".join(donos) if donos else "Desconhecido"

        # Consulta extra via site Registro.br
        try:
            url_whois = f"https://registro.br/tecnologia/ferramentas/whois/?search={domain}"
            resp_site = requests.get(url_whois, timeout=10)
            resp_site.raise_for_status()
            soup = BeautifulSoup(resp_site.text, "html.parser")
            td_owner = soup.find("td", {"class": "cell-ownerhandle"})
            if td_owner:
                span = td_owner.find("span", {"class": "link"})
                if span and span.has_attr("title"):
                    info["Dono/Entidade"] = span["title"].strip()
        except:
            pass

    except Exception as e:
        info["Disponibilidade"] = "Erro"
        info["Origem"] = str(e)

    return info

def consultar_rdap(domain):
    info = {
        "Dominio": domain,
        "Origem": "RDAP.org",
        "Expiração": "",
        "Servidor DNS": "",
        "Disponibilidade": "",
        "Dono/Entidade": ""
    }
    try:
        url = f"https://rdap.org/domain/{domain}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            info["Disponibilidade"] = "Domínio disponível"
            return info
        resp.raise_for_status()
        data = resp.json()
        info["Disponibilidade"] = "Registrado"

        for ev in data.get("events", []):
            if ev.get("eventAction", "").lower() in ["expiration", "expires", "expiry"]:
                info["Expiração"] = formatar_data_br(ev.get("eventDate"))
                break

        ns_list = [ns.get("ldhName") for ns in data.get("nameservers", []) if ns.get("ldhName")]
        info["Servidor DNS"] = ", ".join(ns_list)

        entities = data.get("entities", [])
        donos = [ent.get("handle", "Desconhecido") for ent in entities if ent.get("roles")]
        info["Dono/Entidade"] = ", ".join(donos) if donos else "Desconhecido"

    except Exception as e:
        info["Disponibilidade"] = "Erro"
        info["Origem"] = str(e)

    return info

# ================================
# Função de execução em thread
# ================================
def processar_dominios():
    OUTPUT_FILE = "resultado.csv"
    results = []

    total = len(domains)
    for i, domain in enumerate(domains):
        listbox.insert(tk.END, f"Consultando: {domain}")
        listbox.yview_moveto(1)
        root.update_idletasks()

        if domain.endswith(".br"):
            info = consultar_br(domain)
        else:
            info = consultar_rdap(domain)

        results.append(info)
        # Atualiza barra de progresso
        progress["value"] = (i + 1) / total * 100
        root.update_idletasks()
        time.sleep(1)  # Ajuste para não sobrecarregar os servidores

    # Salva CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["Dominio", "Disponibilidade", "Origem", "Expiração", "Servidor DNS", "Dono/Entidade"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    listbox.insert(tk.END, f"\nConsulta finalizada! Resultados salvos em {OUTPUT_FILE}")
    progress["value"] = 100
    root.update_idletasks()

# ================================
# Janela Tkinter
# ================================
root = tk.Tk()
root.title("Consulta de Domínios")
root.geometry("600x400")

# Listbox
listbox = tk.Listbox(root, width=80, height=20)
listbox.pack(padx=10, pady=10)

# Barra de progresso
progress = ttk.Progressbar(root, length=550)
progress.pack(padx=10, pady=10)

# ================================
# Preparar lista de domínios
# ================================
DOMAINS_FILE = "dominios.txt"
if not os.path.exists(DOMAINS_FILE):
    with open(DOMAINS_FILE, "w") as f:
        f.write("google.com\nregistro.br\nexample.com\ndominiofalso1234567.com\n")

with open(DOMAINS_FILE, "r") as f:
    domains = [line.strip() for line in f if line.strip()]

# ================================
# Executa a consulta automaticamente
# ================================
threading.Thread(target=processar_dominios, daemon=True).start()

# ================================
# Executa a janela
# ================================
root.mainloop()
