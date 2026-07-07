#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  MAĞAZA İÇE AKTARMA KONSOLU  (tek dosya)
  Rakip ürün sayfasını çeker, düzenlemene yardım eder,
  doğrudan Shopify mağazana yükler.

  ÇALIŞTIRMA:
      python magaza_import.py
  Sonra tarayıcıda:  http://localhost:5000

  Gerekli paketler (Flask, requests, beautifulsoup4) eksikse
  ilk çalıştırmada otomatik kurulur.

  ── SHOPIFY TOKEN (otomatik yükleme için) ──────────────────
  Uygulamada  ⚙ Ayarlar  → mağaza adresi + token gir → test et.
  Token nasıl alınır (2026 yöntemi):
    1) https://dev.shopify.com adresine gir → Create app
    2) Admin API erişimini aç, izinler: write_products, read_products
    3) Uygulamayı mağazana kur (install)
    4) API credentials'tan "Admin API access token"ı kopyala (shpat_...)
    5) Ayarlar'a mağaza adresi (magazam.myshopify.com) + token'ı yaz

  ── AI DÜZENLEME (opsiyonel) ────────────────────────────────
  "Yeniden yaz / SEO / çeviri" için Anthropic anahtarı gerekir:
    https://console.anthropic.com → API Keys → sk-ant-...
    Ayarlar'a yapıştır. Anahtar girmezsen diğer her şey çalışır.

  ── YASAL ───────────────────────────────────────────────────
  Rakibin açıklama/görselleri telif taşıyabilir. Yayından önce
  metni "yeniden yaz" ile özgünleştir, görselleri kendininkiyle
  değiştir. Token/anahtar sadece bu klasördeki config.json'da,
  senin bilgisayarında saklanır; paylaşma.
================================================================
"""
import sys, subprocess, importlib

def _ensure(pkgs):
    missing = []
    for mod, pipname in pkgs:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pipname)
    if missing:
        print("Gerekli paketler kuruluyor:", ", ".join(missing), "...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *missing])
        print("Kurulum tamam.\n")

_ensure([("flask", "Flask"), ("requests", "requests"), ("bs4", "beautifulsoup4")])

import os, re, json, html as _html
from urllib.parse import urljoin, urlparse
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
SHOPIFY_API_VERSION = "2026-04"
DEFAULT_MODEL = "claude-sonnet-5"

app = Flask(__name__)



LANDING = """<!doctype html>
<html lang="tr">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MASTER AI — Yapay Zekâ ile Ürün Aktarma</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');
  :root{
    --bg:#0A0B1A;--bg2:#0F1226;--panel:#14172F;--panel2:#1B1F3D;
    --line:#262B4D;--line2:#343A63;--ink:#ECEEFB;--mute:#9298C4;
    --violet:#7C5CFF;--cyan:#33D6FF;--ok:#34D399;--coral:#FF6B6B;
    --grad:linear-gradient(120deg,#7C5CFF 0%,#33D6FF 100%);
  }
  *{box-sizing:border-box}
  html,body{margin:0;scroll-behavior:smooth}
  body{background:var(--bg);color:var(--ink);font-family:'Inter',system-ui,sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1140px;margin:0 auto;padding:0 22px}

  /* atmosphere */
  .glow{position:fixed;border-radius:50%;filter:blur(120px);opacity:.5;z-index:0;pointer-events:none}
  .glow.a{width:520px;height:520px;background:#7C5CFF;top:-160px;left:-120px}
  .glow.b{width:460px;height:460px;background:#33D6FF;top:120px;right:-160px;opacity:.32}
  .content{position:relative;z-index:1}

  /* nav */
  nav{display:flex;align-items:center;justify-content:space-between;padding:20px 0}
  .logo{display:flex;align-items:center;gap:11px}
  .logo .name{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:19px;letter-spacing:-.01em}
  .logo .name b{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
  .navlink{color:var(--mute);font-size:14px;margin-left:22px}
  .navlink:hover{color:var(--ink)}
  .btn{cursor:pointer;border:none;border-radius:11px;padding:13px 22px;font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:15px;display:inline-flex;align-items:center;gap:9px;transition:transform .1s,box-shadow .2s;white-space:nowrap}
  .btn:active{transform:translateY(1px)}
  .btn.grad{background:var(--grad);color:#0A0B1A;box-shadow:0 10px 30px -10px rgba(124,92,255,.6)}
  .btn.grad:hover{box-shadow:0 14px 40px -10px rgba(51,214,255,.6)}
  .btn.ghost{background:transparent;border:1px solid var(--line2);color:var(--ink)}
  .btn.ghost:hover{border-color:var(--cyan);color:var(--cyan)}
  .btn.sm{padding:10px 18px;font-size:14px}

  /* hero */
  .hero{display:grid;grid-template-columns:1.05fr .95fr;gap:40px;align-items:center;padding:56px 0 40px}
  @media(max-width:860px){.hero{grid-template-columns:1fr;gap:34px;padding:34px 0}}
  .eyebrow{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.24em;text-transform:uppercase;color:var(--cyan);display:inline-flex;align-items:center;gap:9px;padding:7px 14px;border:1px solid var(--line2);border-radius:999px;background:rgba(124,92,255,.06)}
  h1{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:52px;line-height:1.05;letter-spacing:-.025em;margin:22px 0 0}
  @media(max-width:860px){h1{font-size:38px}}
  h1 .g{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
  .lead{color:var(--mute);font-size:17px;margin:20px 0 30px;max-width:520px}
  .herocta{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
  .microtrust{margin-top:20px;font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:var(--mute);display:flex;gap:18px;flex-wrap:wrap}
  .microtrust span{display:inline-flex;align-items:center;gap:6px}
  .tick{color:var(--ok)}

  /* hero visual: the flow */
  .flowcard{background:linear-gradient(180deg,var(--panel),var(--bg2));border:1px solid var(--line);border-radius:20px;padding:22px;box-shadow:0 40px 90px -40px rgba(0,0,0,.9)}
  .urlchip{display:flex;align-items:center;gap:9px;background:#0A1020;border:1px solid var(--line2);border-radius:10px;padding:11px 13px;font-family:'IBM Plex Mono',monospace;font-size:12.5px;color:var(--mute)}
  .urlchip .live{width:8px;height:8px;border-radius:50%;background:var(--cyan);box-shadow:0 0 10px var(--cyan);flex:0 0 auto}
  .arrowdown{display:flex;justify-content:center;margin:12px 0;color:var(--violet);font-size:18px}
  .pcard{background:#0A1020;border:1px solid var(--line2);border-radius:14px;overflow:hidden}
  .pcard .ph{height:120px;background:linear-gradient(120deg,rgba(124,92,255,.25),rgba(51,214,255,.18));display:flex;align-items:center;justify-content:center;color:var(--mute);font-family:'IBM Plex Mono',monospace;font-size:11px}
  .pcard .pb{padding:14px}
  .pline{height:9px;border-radius:5px;background:var(--line2);margin-bottom:8px}
  .pline.w70{width:70%}.pline.w45{width:45%}
  .pprice{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:22px;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;margin:10px 0 12px}
  .sendpill{display:inline-flex;align-items:center;gap:8px;background:var(--grad);color:#0A0B1A;font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:13px;padding:9px 15px;border-radius:9px}

  /* sections */
  section{padding:56px 0}
  .kick{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.22em;text-transform:uppercase;color:var(--cyan)}
  h2{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:34px;letter-spacing:-.02em;margin:12px 0 0}
  .sublead{color:var(--mute);font-size:16px;margin-top:12px;max-width:560px}

  .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:36px}
  @media(max-width:780px){.steps{grid-template-columns:1fr}}
  .stepcard{background:linear-gradient(180deg,var(--panel),var(--bg2));border:1px solid var(--line);border-radius:16px;padding:24px;position:relative;overflow:hidden}
  .stepcard .no{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:44px;line-height:1;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;opacity:.9}
  .stepcard h3{font-family:'Space Grotesk',sans-serif;font-size:19px;margin:14px 0 8px;font-weight:600}
  .stepcard p{color:var(--mute);font-size:14.5px;margin:0}
  .stepcard .bar{position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--grad)}

  .feats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:36px}
  @media(max-width:820px){.feats{grid-template-columns:1fr 1fr}}
  @media(max-width:520px){.feats{grid-template-columns:1fr}}
  .feat{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;transition:border .2s,transform .2s}
  .feat:hover{border-color:var(--line2);transform:translateY(-3px)}
  .feat .ic{width:42px;height:42px;border-radius:11px;background:rgba(124,92,255,.12);display:flex;align-items:center;justify-content:center;margin-bottom:14px}
  .feat h4{font-family:'Space Grotesk',sans-serif;font-size:16px;margin:0 0 7px;font-weight:600}
  .feat p{color:var(--mute);font-size:13.5px;margin:0;line-height:1.55}

  /* cta band */
  .band{background:linear-gradient(120deg,rgba(124,92,255,.14),rgba(51,214,255,.10));border:1px solid var(--line2);border-radius:22px;padding:48px 40px;text-align:center;margin:20px 0 10px}
  .band h2{font-size:32px}
  .band p{color:var(--mute);margin:12px auto 26px;max-width:480px}

  footer{border-top:1px solid var(--line);margin-top:40px;padding:30px 0;display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;color:var(--mute);font-size:13px}

  @media (prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
</style>

<div class="glow a"></div><div class="glow b"></div>
<div class="content">
<div class="wrap">

  <nav>
    <div class="logo">
      <svg width="38" height="38" viewBox="0 0 48 48" aria-hidden="true">
        <defs><linearGradient id="mg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7C5CFF"/><stop offset="1" stop-color="#33D6FF"/></linearGradient></defs>
        <rect x="3" y="3" width="42" height="42" rx="13" fill="url(#mg)"/>
        <path d="M13 34 V15 L24 27 L35 15 V34" fill="none" stroke="#0A0B1A" stroke-width="3.6" stroke-linejoin="round" stroke-linecap="round"/>
      </svg>
      <div class="name">MASTER <b>AI</b></div>
    </div>
    <div>
      <a class="navlink" href="#nasil">Nasıl çalışır</a>
      <a class="navlink" href="#ozellikler">Özellikler</a>
      <a class="btn grad sm" href="/konsol" style="margin-left:22px">Konsolu Aç →</a>
    </div>
  </nav>

  <!-- HERO -->
  <div class="hero">
    <div>
      <span class="eyebrow"><span class="tick">✦</span> Yapay zekâ ile ürün aktarma</span>
      <h1>Ürünü <span class="g">çek</span>, yapay zekâ <span class="g">düzenlesin</span>, mağazana <span class="g">gönder</span>.</h1>
      <p class="lead">Bir ürün bağlantısı yapıştır. MASTER AI ürünü çeker, başlığı ve açıklamayı özgünleştirir, fiyatını kâr marjınla ayarlar, görselleri düzenler ve tek tuşla Shopify mağazana yükler.</p>
      <div class="herocta">
        <a class="btn grad" href="/konsol">Konsolu Aç →</a>
        <a class="btn ghost" href="#nasil">Nasıl çalışır?</a>
      </div>
      <div class="microtrust">
        <span><span class="tick">✓</span> Herhangi bir ürün bağlantısı</span>
        <span><span class="tick">✓</span> Tek tuşla Shopify</span>
        <span><span class="tick">✓</span> SEO & kâr marjı</span>
      </div>
    </div>

    <div class="flowcard">
      <div class="urlchip"><span class="live"></span> rakip-magaza.com/urun/… <span style="margin-left:auto;color:var(--cyan)">çek →</span></div>
      <div class="arrowdown">↓ yapay zekâ çözümlüyor ↓</div>
      <div class="pcard">
        <div class="ph">ürün görseli</div>
        <div class="pb">
          <div class="pline w70"></div><div class="pline w45"></div>
          <div class="pprice">₺1.299,90</div>
          <span class="sendpill">⤴ Shopify'a gönder</span>
        </div>
      </div>
    </div>
  </div>

  <!-- HOW -->
  <section id="nasil">
    <div class="kick">Üç adımda</div>
    <h2>Nasıl çalışır?</h2>
    <p class="sublead">Karmaşık kurulum yok. Bir bağlantı ver, gerisini yapay zekâ hallensin.</p>
    <div class="steps">
      <div class="stepcard"><div class="bar"></div><div class="no">01</div><h3>Çek</h3><p>Rakip ürün sayfasının bağlantısını yapıştır. MASTER AI sayfayı çekip başlık, fiyat, açıklama, görsel ve özellikleri otomatik çıkarır.</p></div>
      <div class="stepcard"><div class="bar"></div><div class="no">02</div><h3>Düzenle</h3><p>Metni yapay zekâ ile özgünleştir, fiyatı kâr marjınla ayarla, görselleri seç, SEO başlığı ve etiketleri tek tuşla üret.</p></div>
      <div class="stepcard"><div class="bar"></div><div class="no">03</div><h3>Gönder</h3><p>Taslak ya da yayında olarak seç, "Gönder"e bas. Ürün saniyeler içinde Shopify mağazanda hazır.</p></div>
    </div>
  </section>

  <!-- FEATURES -->
  <section id="ozellikler">
    <div class="kick">Neler yapar</div>
    <h2>Tek panelde her şey</h2>
    <p class="sublead">Rakip araştırmasından mağazaya yüklemeye kadar bütün akış tek yerde.</p>
    <div class="feats">
      <div class="feat"><div class="ic">🔗</div><h4>Bağlantıdan çekme</h4><p>Herhangi bir ürün sayfasının linkinden başlık, fiyat, açıklama, görsel ve özellikleri anında al.</p></div>
      <div class="feat"><div class="ic">✍️</div><h4>AI ile yeniden yazma</h4><p>Başlık ve açıklamayı seçtiğin tonda, tamamen özgün ve satış odaklı biçimde yeniden yaz.</p></div>
      <div class="feat"><div class="ic">📈</div><h4>SEO & satış CTA'ları</h4><p>SEO başlığı, meta açıklama, etiket ve URL handle'ını tek tuşla üret.</p></div>
      <div class="feat"><div class="ic">💰</div><h4>Fiyat & kâr marjı</h4><p>Alış fiyatı, döviz kuru, kâr marjı ve psikolojik yuvarlama ile satış fiyatını hesapla.</p></div>
      <div class="feat"><div class="ic">🖼️</div><h4>Görsel düzenleme</h4><p>Görselleri seç, ana görseli belirle, gereksizleri çıkar, kendi fotoğraflarını ekle.</p></div>
      <div class="feat"><div class="ic">⚡</div><h4>Tek tuşla Shopify</h4><p>Hazır ürünü doğrudan mağazana yükle; CSV, panel, kopyala-yapıştır derdi yok.</p></div>
    </div>
  </section>

  <!-- CTA -->
  <div class="band">
    <div class="kick">Hazır mısın?</div>
    <h2>İlk ürününü şimdi aktar</h2>
    <p>Bir bağlantı yapıştır, yapay zekânın işi devralmasını izle.</p>
    <a class="btn grad" href="/konsol">Konsolu Aç →</a>
  </div>

  <footer>
    <div class="logo"><svg width="26" height="26" viewBox="0 0 48 48" aria-hidden="true"><rect x="3" y="3" width="42" height="42" rx="13" fill="url(#mg)"/><path d="M13 34 V15 L24 27 L35 15 V34" fill="none" stroke="#0A0B1A" stroke-width="3.6" stroke-linejoin="round" stroke-linecap="round"/></svg><span style="font-family:'Space Grotesk';font-weight:600">MASTER AI</span></div>
    <div>© 2026 MASTER AI · Kişisel yapay zekâ aracı</div>
  </footer>

</div>
</div>
</html>
"""

HTML = """<!doctype html>
<html lang="tr">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MASTER AI — Konsol</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap');
  :root{
    --bg:#0A0B1A;--bg2:#0F1226;--panel:#14172F;--panel2:#1B1F3D;
    --line:#262B4D;--line2:#343A63;--ink:#ECEEFB;--mute:#9298C4;
    --amber:#7C5CFF;--teal:#33D6FF;--coral:#FF6B6B;--ok:#34D399;
    --shadow:0 24px 60px -30px rgba(0,0,0,.8);
  }
  *{box-sizing:border-box}
  html,body{margin:0}
  body{background:radial-gradient(1200px 500px at 15% -10%,#1A1640 0%,transparent 60%),var(--bg);color:var(--ink);font-family:'Inter',system-ui,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased;min-height:100vh}
  .wrap{max-width:1160px;margin:0 auto;padding:24px 20px 90px}
  header.top{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:20px;padding-bottom:18px;border-bottom:1px solid var(--line)}
  .brand .kick{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.28em;color:var(--teal);text-transform:uppercase}
  .brand h1{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:25px;margin:2px 0 0;letter-spacing:-.02em}
  .brand h1 span{color:var(--amber)}
  .topright{display:flex;gap:9px;align-items:center;flex-wrap:wrap}
  .chip{font-family:'IBM Plex Mono',monospace;font-size:11px;padding:6px 11px;border:1px solid var(--line2);border-radius:999px;color:var(--mute);display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--mute)}
  .chip.on .dot{background:var(--ok)} .chip.off .dot{background:var(--coral)} .chip.busy .dot{background:var(--amber);animation:pulse 1.1s infinite}
  @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(124,92,255,.5)}70%{box-shadow:0 0 0 6px rgba(124,92,255,0)}100%{box-shadow:0 0 0 0 rgba(124,92,255,0)}}

  .step{background:linear-gradient(180deg,var(--panel),var(--bg2));border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:18px;box-shadow:var(--shadow)}
  .stephead{display:flex;align-items:center;gap:12px;margin-bottom:14px}
  .num{font-family:'IBM Plex Mono',monospace;font-size:12px;color:#fff;background:var(--amber);border-radius:6px;padding:3px 8px}
  .stephead h2{font-family:'Space Grotesk',sans-serif;font-size:15px;letter-spacing:.02em;margin:0;text-transform:uppercase;font-weight:500}
  .stephead .hint{margin-left:auto;color:var(--mute);font-size:12px}

  input,textarea,select{background:#0A1417;border:1px solid var(--line2);color:var(--ink);border-radius:9px;padding:12px 13px;font-family:'IBM Plex Mono',monospace;font-size:13px;outline:none;transition:border .15s,box-shadow .15s;width:100%}
  textarea{line-height:1.55;resize:vertical}
  input:focus,textarea:focus,select:focus{border-color:var(--amber);box-shadow:0 0 0 3px rgba(124,92,255,.13)}
  .srcrow{display:flex;gap:10px;flex-wrap:wrap}
  .srcrow input{flex:1;min-width:220px}
  .btn{cursor:pointer;border:none;border-radius:9px;padding:12px 20px;font-family:'Space Grotesk',sans-serif;font-weight:500;font-size:14px;display:inline-flex;align-items:center;gap:8px;transition:transform .08s,filter .15s;white-space:nowrap}
  .btn:active{transform:translateY(1px)}
  .btn.primary{background:var(--amber);color:#fff}.btn.primary:hover{filter:brightness(1.06)}
  .btn.teal{background:var(--teal);color:#0A0B1A}.btn.teal:hover{filter:brightness(1.05)}
  .btn.ghost{background:transparent;border:1px solid var(--line2);color:var(--ink)}.btn.ghost:hover{border-color:var(--teal);color:var(--teal)}
  .btn.small{padding:9px 14px;font-size:13px}
  .btn:disabled{opacity:.45;cursor:not-allowed}
  .btn.send{background:var(--ok);color:#052a17;font-size:15px;padding:14px 26px}
  .statusline{font-family:'IBM Plex Mono',monospace;font-size:12.5px;color:var(--mute);margin-top:14px;min-height:18px}
  .statusline.err{color:var(--coral)} .statusline b{color:var(--teal);font-weight:500}

  #workspace{display:none} #workspace.on{display:block}
  .cols{display:grid;grid-template-columns:1fr 330px;gap:18px}
  @media(max-width:840px){.cols{grid-template-columns:1fr}}

  .tabs{display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:2px}
  .tab{cursor:pointer;padding:9px 14px;font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.05em;color:var(--mute);border:none;background:none;border-bottom:2px solid transparent;text-transform:uppercase}
  .tab.active{color:var(--amber);border-bottom-color:var(--amber)}
  .pane{display:none} .pane.active{display:block}

  .field{margin-bottom:13px}
  label.lab{display:block;font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--mute);margin-bottom:6px}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:520px){.grid2{grid-template-columns:1fr}}
  .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
  .toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;padding-top:14px;border-top:1px dashed var(--line2)}

  .imgs{display:flex;gap:9px;flex-wrap:wrap}
  .thumb{position:relative;width:74px;height:74px;border-radius:9px;overflow:hidden;border:2px solid var(--line2);background:#0A1417;cursor:pointer}
  .thumb.use{border-color:var(--teal)} .thumb.main{border-color:var(--amber)}
  .thumb img{width:100%;height:100%;object-fit:cover;opacity:.4;transition:.15s}
  .thumb.use img{opacity:1}
  .thumb .x{position:absolute;top:2px;right:2px;width:19px;height:19px;border-radius:50%;background:rgba(10,20,23,.85);color:#fff;border:none;cursor:pointer;font-size:12px;line-height:19px;padding:0}
  .thumb .badge{position:absolute;bottom:0;left:0;right:0;font-family:'IBM Plex Mono',monospace;font-size:8px;text-align:center;letter-spacing:.1em;padding:1px}
  .thumb.main .badge{background:var(--amber);color:#fff}
  .imghint{color:var(--mute);font-size:11.5px;margin-top:8px;font-family:'IBM Plex Mono',monospace}
  .noimg{color:var(--mute);font-size:12px;font-family:'IBM Plex Mono',monospace;padding:8px 0}

  .spec{display:grid;grid-template-columns:1fr 1fr 32px;gap:8px;margin-bottom:7px}
  .spec .del{background:none;border:1px solid var(--line2);color:var(--mute);border-radius:7px;cursor:pointer}.spec .del:hover{color:var(--coral);border-color:var(--coral)}
  .empty{color:var(--mute);font-family:'IBM Plex Mono',monospace;font-size:12px;padding:6px 0}

  .calc{background:#0A1417;border:1px solid var(--line2);border-radius:10px;padding:14px;margin-top:12px}
  .calc .final{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:26px;color:var(--ok)}
  .calc .flabel{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.16em;color:var(--mute);text-transform:uppercase}

  .preview{position:sticky;top:16px}
  .plabel{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.2em;color:var(--mute);text-transform:uppercase;margin-bottom:9px}
  .pcard{background:#0A1417;border:1px solid var(--line2);border-radius:12px;overflow:hidden}
  .pimg{width:100%;aspect-ratio:1;background:#0d1c20 center/cover no-repeat;display:flex;align-items:center;justify-content:center;color:var(--mute);font-family:'IBM Plex Mono',monospace;font-size:11px}
  .pbody{padding:15px}
  .ptitle{font-family:'Space Grotesk',sans-serif;font-weight:500;font-size:16px;margin:0 0 8px;line-height:1.3}
  .pprice{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:22px;color:var(--amber);margin-bottom:10px}
  .pdesc{font-size:12.5px;color:var(--mute);max-height:120px;overflow:auto;white-space:pre-line}
  .note{margin-top:14px;font-size:12px;color:var(--mute);line-height:1.55;border-left:2px solid var(--amber);padding-left:12px}
  .note b{color:var(--amber)}

  .sendrow{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
  .segmented{display:inline-flex;border:1px solid var(--line2);border-radius:9px;overflow:hidden}
  .segmented button{background:none;border:none;color:var(--mute);padding:11px 16px;cursor:pointer;font-family:'IBM Plex Mono',monospace;font-size:12px}
  .segmented button.on{background:var(--panel2);color:var(--ink)}
  .pushresult{margin-top:14px;font-size:13px}
  .pushresult a{color:var(--teal)}

  /* modal */
  .overlay{position:fixed;inset:0;background:rgba(4,12,14,.72);display:none;align-items:center;justify-content:center;padding:20px;z-index:40}
  .overlay.on{display:flex}
  .modal{background:var(--panel);border:1px solid var(--line2);border-radius:14px;max-width:520px;width:100%;padding:24px;box-shadow:var(--shadow)}
  .modal h3{font-family:'Space Grotesk',sans-serif;margin:0 0 4px;font-size:19px}
  .modal .sub{color:var(--mute);font-size:12.5px;margin-bottom:18px}
  .modal .field label.lab{margin-top:2px}
  .modal .foot{display:flex;gap:10px;justify-content:space-between;align-items:center;margin-top:18px;flex-wrap:wrap}
  .link{color:var(--teal);font-size:11.5px;text-decoration:none}.link:hover{text-decoration:underline}
  .testline{font-family:'IBM Plex Mono',monospace;font-size:11.5px;margin-top:8px;min-height:16px;color:var(--mute)}

  #toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(20px);background:var(--panel2);border:1px solid var(--line2);color:var(--ink);padding:12px 20px;border-radius:10px;font-size:13px;opacity:0;pointer-events:none;transition:.25s;z-index:60;font-family:'IBM Plex Mono',monospace}
  #toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
  @media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>

<div class="wrap">
  <header class="top">
    <div class="brand" style="display:flex;align-items:center;gap:12px">
      <svg width="34" height="34" viewBox="0 0 48 48" aria-hidden="true">
        <defs><linearGradient id="mg2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7C5CFF"/><stop offset="1" stop-color="#33D6FF"/></linearGradient></defs>
        <rect x="3" y="3" width="42" height="42" rx="13" fill="url(#mg2)"/>
        <path d="M13 34 V15 L24 27 L35 15 V34" fill="none" stroke="#0A0B1A" stroke-width="3.6" stroke-linejoin="round" stroke-linecap="round"/>
      </svg>
      <div>
        <div class="kick">İçe Aktarma Konsolu</div>
        <h1 style="margin-top:2px">MASTER <span>AI</span></h1>
      </div>
    </div>
    <div class="topright">
      <a class="btn ghost small" href="/" style="text-decoration:none">← Ana sayfa</a>
      <span class="chip off" id="chipShop"><span class="dot"></span>Shopify</span>
      <span class="chip off" id="chipAI"><span class="dot"></span>AI</span>
      <button class="btn ghost small" onclick="openSettings()">⚙ Ayarlar</button>
    </div>
  </header>

  <!-- STEP 1 -->
  <section class="step">
    <div class="stephead"><span class="num">01</span><h2>Kaynak</h2><span class="hint">rakip ürün sayfasının bağlantısı</span></div>
    <div class="srcrow">
      <input type="url" id="url" placeholder="https://rakip-magaza.com/urun/...">
      <button class="btn primary" id="fetchBtn" onclick="doFetch()">Çek →</button>
    </div>
    <div class="statusline" id="status"></div>
  </section>

  <!-- WORKSPACE -->
  <div id="workspace">
    <section class="step">
      <div class="stephead"><span class="num">02</span><h2>Düzenle</h2><span class="hint">beğenmediğin her şeyi değiştir</span></div>
      <div class="cols">
        <div>
          <div class="tabs">
            <button class="tab active" onclick="tab('content',this)">İçerik</button>
            <button class="tab" onclick="tab('price',this)">Fiyat / Marj</button>
            <button class="tab" onclick="tab('media',this)">Görseller</button>
            <button class="tab" onclick="tab('seo',this)">SEO / Etiket</button>
          </div>

          <!-- CONTENT -->
          <div class="pane active" id="pane-content">
            <div class="field"><label class="lab">Başlık</label><input id="f_title" oninput="sync()"></div>
            <div class="field"><label class="lab">Açıklama</label><textarea id="f_desc" rows="6" oninput="sync()"></textarea></div>
            <div class="grid2">
              <div class="field"><label class="lab">Marka</label><input id="f_vendor"></div>
              <div class="field"><label class="lab">SKU / Stok kodu</label><input id="f_sku"></div>
            </div>
            <div class="field"><label class="lab">Özellikler</label><div id="specs"></div>
              <button class="btn ghost small" style="margin-top:4px" onclick="addSpec('','')">+ özellik ekle</button>
            </div>
            <div class="toolbar" style="flex-direction:column;align-items:stretch;gap:10px">
              <button class="btn primary" id="listingBtn" onclick="aiListing()" style="justify-content:center;font-size:15px">✦ Profesyonel listeleme oluştur</button>
              <div style="font-size:11.5px;color:var(--mute);line-height:1.5">Açıklama + fayda maddeleri + nasıl kullanılır + özellik tablosu + güven bölümü (garanti / kargo / iade) + SSS — hepsi tek tuşla, ürüne özel üretilir.</div>
              <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:2px">
                <select id="tone" style="width:auto;flex:0 0 auto">
                  <option>satış odaklı</option><option>sade ve net</option><option>lüks / premium</option><option>samimi</option>
                </select>
                <button class="btn teal small" id="rewriteBtn" onclick="aiRewrite()">Sadece başlık & açıklamayı yeniden yaz</button>
              </div>
            </div>
          </div>

          <!-- PRICE -->
          <div class="pane" id="pane-price">
            <div style="font-size:12px;color:var(--mute);margin-bottom:12px;line-height:1.55">Tüm gerçek maliyetleri gir; araç kâr edeceğin <b style="color:var(--cyan)">önerilen satış fiyatını</b> hesaplar. Varsayılanlar Türkiye/Shopify için makul başlangıçtır — kendi rakamlarınla değiştir.</div>
            <div class="plabel" style="margin:2px 0 8px">Maliyetler</div>
            <div class="grid2">
              <div class="field"><label class="lab">Ürün maliyeti (alış)</label><input id="p_cost" oninput="calc()"></div>
              <div class="field"><label class="lab">Para birimi</label><select id="p_srccur" onchange="calc()"><option>TRY</option><option>USD</option><option>EUR</option><option>GBP</option></select></div>
            </div>
            <div class="grid2">
              <div class="field"><label class="lab">Kur (1 birim = ₺)</label><input id="p_fx" value="1" oninput="calc()"></div>
              <div class="field"><label class="lab">Kargo maliyeti (₺)</label><input id="p_ship" value="0" oninput="calc()"></div>
            </div>
            <div class="plabel" style="margin:14px 0 8px">Kesintiler (satış fiyatının %\'si)</div>
            <div class="grid2">
              <div class="field"><label class="lab">Ödeme komisyonu %</label><input id="p_pay" value="5" oninput="calc()"></div>
              <div class="field"><label class="lab">Platform / işlem %</label><input id="p_platform" value="2" oninput="calc()"></div>
            </div>
            <div class="grid2">
              <div class="field"><label class="lab">Reklam payı %</label><input id="p_ad" value="25" oninput="calc()"></div>
              <div class="field"><label class="lab">İade / kayıp payı %</label><input id="p_return" value="4" oninput="calc()"></div>
            </div>
            <div class="grid2">
              <div class="field"><label class="lab">KDV %</label><input id="p_vat" value="20" oninput="calc()"></div>
              <div class="field"><label class="lab">Hedef net kâr %</label><input id="p_margin" value="20" oninput="calc()"></div>
            </div>
            <label class="lab" style="display:flex;align-items:center;gap:8px;text-transform:none;letter-spacing:0;font-size:12.5px;color:var(--ink)"><input type="checkbox" id="p_vatinc" checked onchange="calc()" style="width:auto"> Fiyata KDV dahil (Türkiye standardı)</label>
            <div class="calc">
              <div class="flabel">Önerilen satış fiyatı</div>
              <div class="final" id="p_final">—</div>
              <div id="p_breakdown" style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:var(--mute);margin-top:10px;line-height:1.75"></div>
              <div class="grid2" style="margin-top:12px">
                <div class="field" style="margin:0"><label class="lab">Karşılaştırma çarpanı</label><input id="p_compmult" value="1.5" oninput="calc()"></div>
                <div class="field" style="margin:0"><label class="lab">Yuvarlama</label><select id="p_round" onchange="calc()"><option value="90">…,90</option><option value="99">…,99</option><option value="int">tam</option><option value="none">yok</option></select></div>
              </div>
              <button class="btn primary small" style="margin-top:12px" onclick="applyPrice()">Bu fiyatları uygula</button>
            </div>
          </div>

          <!-- MEDIA -->
          <div class="pane" id="pane-media">
            <label class="lab">Görselleri seç — tıkla: kullan/kullanma · ⭐ ile ana görsel</label>
            <div class="imgs" id="imgs"></div>
            <div class="imghint" id="imgcount"></div>
            <div class="row" style="margin-top:12px">
              <input id="addimg" placeholder="Kendi görsel URL'ini ekle (https://...)" style="flex:1">
              <button class="btn ghost small" onclick="addImgUrl()">Ekle</button>
            </div>
          </div>

          <!-- SEO -->
          <div class="pane" id="pane-seo">
            <div class="field"><label class="lab">SEO başlığı</label><input id="s_title" oninput="collectSeo()"></div>
            <div class="field"><label class="lab">Meta açıklama</label><textarea id="s_meta" rows="2" oninput="collectSeo()"></textarea></div>
            <div class="field"><label class="lab">Etiketler (virgülle)</label><input id="s_tags" oninput="collectSeo()"></div>
            <div class="field"><label class="lab">URL handle</label><input id="s_handle" oninput="collectSeo()"></div>
            <div class="toolbar">
              <button class="btn teal small" id="seoBtn" onclick="aiSeo()">✦ SEO üret</button>
              <select id="tlang" style="width:auto;flex:0 0 auto"><option>Türkçe</option><option>İngilizce</option><option>Almanca</option></select>
              <button class="btn ghost small" id="trBtn" onclick="aiTranslate()">Başlık/açıklamayı çevir</button>
            </div>
          </div>
        </div>

        <!-- PREVIEW -->
        <div class="preview">
          <div class="plabel">Mağaza önizlemesi</div>
          <div class="pcard">
            <div class="pimg" id="v_img">görsel yok</div>
            <div class="pbody">
              <h3 class="ptitle" id="v_title">—</h3>
              <div class="pprice" id="v_price">—</div>
              <div class="pdesc" id="v_desc"></div>
            </div>
          </div>
          <div class="note"><b>Not:</b> Açıklama ve görseller telif taşıyabilir. Yayından önce metni "yeniden yaz" ile özgünleştir; görselleri kendi fotoğraflarınla değiştir.</div>
        </div>
      </div>
      <div id="proWrap" style="display:none;margin-top:18px">
        <div class="plabel">Profesyonel sayfa önizlemesi — Shopify'da böyle görünecek</div>
        <div id="proPreview" style="background:#fff;color:#111;border-radius:12px;padding:22px;max-height:560px;overflow:auto"></div>
      </div>
    </section>

    <!-- STEP 3 -->
    <section class="step">
      <div class="stephead"><span class="num">03</span><h2>Shopify'a Gönder</h2><span class="hint">tek tuşla yükle</span></div>
      <div class="sendrow">
        <div class="segmented" id="statusSeg">
          <button class="on" data-v="draft" onclick="setPubStatus('draft',this)">Taslak</button>
          <button data-v="active" onclick="setPubStatus('active',this)">Yayında</button>
        </div>
        <div class="field" style="margin:0"><input id="f_inv" placeholder="Stok adedi (ops.)" style="width:150px"></div>
        <button class="btn send" id="pushBtn" onclick="doPush()">Mağazaya gönder ⤴</button>
      </div>
      <div class="pushresult" id="pushresult"></div>
    </section>
  </div>
</div>

<!-- SETTINGS MODAL -->
<div class="overlay" id="overlay">
  <div class="modal">
    <h3>Ayarlar</h3>
    <div class="sub">Bilgiler yalnızca senin bilgisayarında <code>config.json</code> dosyasında saklanır.</div>
    <div class="field"><label class="lab">Shopify mağaza adresi</label><input id="c_store" placeholder="magazam.myshopify.com"></div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:var(--cyan);margin:0 0 8px;line-height:1.5">Dev Dashboard (2026): Client ID + Gizli anahtarı gir; token'ı araç otomatik üretir.</div>
    <div class="grid2">
      <div class="field"><label class="lab">Client ID</label><input id="c_client_id" placeholder="Dev Dashboard → Client ID"></div>
      <div class="field"><label class="lab">Gizli anahtar (Client secret)</label><input id="c_client_secret" placeholder="Gizli anahtar" type="password"></div>
    </div>
    <div class="field"><label class="lab">veya doğrudan Admin API token (eski yöntem, varsa)</label><input id="c_token" placeholder="shpat_..." type="password"></div>
    <div class="row"><button class="btn ghost small" onclick="testShopify()">Bağlantıyı test et</button><span class="testline" id="testline"></span></div>
    <div class="field" style="margin-top:16px"><label class="lab">Anthropic API anahtarı (AI düzenleme için)</label><input id="c_key" placeholder="sk-ant-..." type="password"></div>
    <div class="field"><label class="lab">Model</label><input id="c_model" placeholder="claude-sonnet-5"></div>
    <div style="border-top:1px solid var(--line2);margin:14px 0 8px;padding-top:14px;font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--cyan)">Güven bilgileri (profesyonel listelemede kullanılır)</div>
    <div class="field"><label class="lab">Mağaza adı</label><input id="c_store_name" placeholder="MASTER AI Store"></div>
    <div class="grid2">
      <div class="field"><label class="lab">Garanti</label><input id="c_guarantee" placeholder="Kalite garantisi"></div>
      <div class="field"><label class="lab">Kargo</label><input id="c_shipping" placeholder="2-4 iş günü kargo"></div>
    </div>
    <div class="grid2">
      <div class="field"><label class="lab">İade</label><input id="c_returns" placeholder="14 gün kolay iade"></div>
      <div class="field"><label class="lab">Ödeme</label><input id="c_payment" placeholder="SSL güvenli ödeme"></div>
    </div>
    <div class="foot">
      <a class="link" href="https://dev.shopify.com" target="_blank">Shopify token nasıl alınır? →</a>
      <div class="row">
        <button class="btn ghost small" onclick="closeSettings()">Kapat</button>
        <button class="btn primary small" onclick="saveSettings()">Kaydet</button>
      </div>
    </div>
  </div>
</div>

<div id="toast"></div>

<script>
const $=id=>document.getElementById(id);
let P={title:"",price:"",currency:"TRY",description:"",images:[],vendor:"",sku:"",tags:[],specs:[],seo:{},body_html:"",compare_at_price:""};
let pubStatus="draft";
function toast(m){const t=$("toast");t.textContent=m;t.classList.add("show");setTimeout(()=>t.classList.remove("show"),2300);}
function stat(m,e){const s=$("status");s.className="statusline"+(e?" err":"");s.innerHTML=m;}

/* ---- tabs ---- */
function tab(name,el){document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));el.classList.add("active");
  document.querySelectorAll(".pane").forEach(p=>p.classList.remove("active"));$("pane-"+name).classList.add("active");}

/* ---- config ---- */
async function loadConfig(){
  try{const c=await (await fetch("/api/config")).json();
    $("chipShop").className="chip "+(c.shopify_ready?"on":"off");
    $("chipAI").className="chip "+(c.ai_ready?"on":"off");
    $("c_store").value=c.shopify_store||"";$("c_model").value=c.model||"claude-sonnet-5";
    $("c_client_id").value=c.shopify_client_id||"";
    $("c_store_name").value=c.store_name||"";$("c_guarantee").value=c.trust_guarantee||"";
    $("c_shipping").value=c.trust_shipping||"";$("c_returns").value=c.trust_returns||"";
    $("c_payment").value=c.trust_payment||"";
  }catch(e){}
}
function openSettings(){$("overlay").classList.add("on");}
function closeSettings(){$("overlay").classList.remove("on");}
async function saveSettings(){
  const body={shopify_store:$("c_store").value,model:$("c_model").value,
    store_name:$("c_store_name").value,trust_guarantee:$("c_guarantee").value,
    trust_shipping:$("c_shipping").value,trust_returns:$("c_returns").value,trust_payment:$("c_payment").value};
  if($("c_token").value)body.shopify_token=$("c_token").value;
  if($("c_client_id").value)body.shopify_client_id=$("c_client_id").value;
  if($("c_client_secret").value)body.shopify_client_secret=$("c_client_secret").value;
  if($("c_key").value)body.anthropic_key=$("c_key").value;
  await fetch("/api/settings",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  toast("Ayarlar kaydedildi ✓");$("c_token").value="";$("c_key").value="";$("c_client_secret").value="";closeSettings();loadConfig();
}
async function testShopify(){
  $("testline").textContent="test ediliyor…";
  {
    const b={shopify_store:$("c_store").value};
    if($("c_token").value)b.shopify_token=$("c_token").value;
    if($("c_client_id").value)b.shopify_client_id=$("c_client_id").value;
    if($("c_client_secret").value)b.shopify_client_secret=$("c_client_secret").value;
    await fetch("/api/settings",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)});
  }
  try{const r=await (await fetch("/api/test-shopify",{method:"POST"})).json();
    $("testline").textContent=r.ok?("✓ bağlandı: "+r.name):("✗ "+r.error);
    $("testline").style.color=r.ok?"var(--ok)":"var(--coral)";loadConfig();
  }catch(e){$("testline").textContent="✗ "+e;}
}

/* ---- fetch ---- */
async function doFetch(){
  const url=$("url").value.trim();
  if(!url){stat("Önce bir bağlantı gir.",true);return;}
  $("fetchBtn").disabled=true;stat("Sayfa çekiliyor ve <b>çözümleniyor</b>…");
  try{
    const r=await fetch("/api/fetch",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url})});
    const d=await r.json();
    if(!r.ok){stat("✗ "+(d.error||"Çekilemedi"),true);return;}
    P={title:d.title||"",price:d.price||"",currency:d.currency||"TRY",description:d.description||"",
       images:(d.images||[]).map(s=>({src:s,use:true})),vendor:d.vendor||"",sku:d.sku||"",
       tags:d.tags||[],specs:d.specs||[],seo:{},body_html:"",compare_at_price:""};
    $("proWrap").style.display="none";$("proPreview").innerHTML="";
    fill();$("workspace").classList.add("on");
    stat("Ürün hazır. Aşağıda düzenleyip mağazana gönder.");
    $("workspace").scrollIntoView({behavior:"smooth",block:"start"});
  }catch(e){stat("✗ Bağlantı hatası: "+e,true);}
  finally{$("fetchBtn").disabled=false;}
}

/* ---- fill editor ---- */
function fill(){
  $("f_title").value=P.title;$("f_desc").value=P.description;
  $("f_vendor").value=P.vendor;$("f_sku").value=P.sku;
  $("p_cost").value=P.price;$("p_srccur").value=P.currency||"TRY";
  $("s_tags").value=(P.tags||[]).join(", ");
  renderSpecs();renderImgs();calc();sync();
}
function renderSpecs(){const b=$("specs");b.innerHTML="";
  if(!P.specs.length){b.innerHTML='<div class="empty">özellik yok</div>';return;}
  P.specs.forEach((s,i)=>{const r=document.createElement("div");r.className="spec";
    r.innerHTML=`<input placeholder="özellik" value="${(s.name||'').replace(/"/g,'&quot;')}" oninput="P.specs[${i}].name=this.value">
      <input placeholder="değer" value="${(s.value||'').replace(/"/g,'&quot;')}" oninput="P.specs[${i}].value=this.value">
      <button class="del" onclick="P.specs.splice(${i},1);renderSpecs()">×</button>`;b.appendChild(r);});}
function addSpec(n,v){P.specs.push({name:n,value:v});renderSpecs();}

/* ---- images ---- */
function renderImgs(){const b=$("imgs");
  if(!P.images.length){b.innerHTML='<div class="noimg">görsel yok</div>';$("imgcount").textContent="";return;}
  b.innerHTML="";
  P.images.forEach((im,i)=>{const d=document.createElement("div");
    d.className="thumb"+(im.use?" use":"")+(i===0&&im.use?" main":"");
    d.innerHTML=`<img src="${im.src}" onerror="this.parentNode.style.display='none'">
      ${im.use&&i===0?'<div class="badge">ANA</div>':''}
      <button class="x" onclick="event.stopPropagation();P.images.splice(${i},1);renderImgs();sync()">×</button>`;
    d.onclick=()=>{im.use=!im.use;renderImgs();sync();};
    if(im.use){const star=document.createElement("button");star.className="x";star.style.left="2px";star.style.right="auto";
      star.textContent="⭐";star.title="ana görsel yap";
      star.onclick=(e)=>{e.stopPropagation();P.images.splice(0,0,P.images.splice(i,1)[0]);renderImgs();sync();};
      d.appendChild(star);}
    b.appendChild(d);});
  const used=P.images.filter(x=>x.use).length;
  $("imgcount").textContent=used+" görsel içe aktarılacak · "+P.images.length+" toplam";
}
function addImgUrl(){const u=$("addimg").value.trim();if(!u.startsWith("http"))return toast("Geçerli URL gir");
  P.images.push({src:u,use:true});$("addimg").value="";renderImgs();sync();}

/* ---- pricing ---- */
function num(v){v=parseFloat(String(v).replace(",","."));return isNaN(v)?0:v;}
function roundP(x,mode){if(mode==="int")return Math.round(x);if(mode==="90")return Math.max(0,Math.ceil(x)-0.10);if(mode==="99")return Math.max(0,Math.ceil(x)-0.01);return x;}
function calc(){
  const cost=num($("p_cost").value),fx=num($("p_fx").value)||1,cur=$("p_srccur").value,ship=num($("p_ship").value);
  const pay=num($("p_pay").value)/100,plat=num($("p_platform").value)/100,ad=num($("p_ad").value)/100,
        ret=num($("p_return").value)/100,vat=num($("p_vat").value)/100,margin=num($("p_margin").value)/100;
  const vatInc=$("p_vatinc").checked;
  const C=cost*(cur==="TRY"?1:fx)+ship;
  const vatFrac=vatInc?(vat/(1+vat)):0;
  const S=pay+plat+ad+ret+vatFrac, denom=1-S-margin;
  const bd=$("p_breakdown");
  if(denom<=0){$("p_final").textContent="—";bd.innerHTML='<span style="color:var(--coral)">Maliyet + kesintiler + hedef kâr %100\'ü aşıyor. Reklam/kâr oranını düşür.</span>';P._final=0;P._comp=0;return;}
  const Pr=roundP(C/denom,$("p_round").value);P._final=Pr;
  const vatAmt=Pr*vatFrac,payAmt=Pr*pay,platAmt=Pr*plat,adAmt=Pr*ad,retAmt=Pr*ret;
  const net=Pr-C-vatAmt-payAmt-platAmt-adAmt-retAmt, netPct=Pr>0?net/Pr*100:0;
  const beforeAds=Pr-C-vatAmt-payAmt-platAmt-retAmt, beRoas=(adAmt>0&&beforeAds>0)?Pr/beforeAds:0;
  const comp=roundP(Pr*(num($("p_compmult").value)||1),$("p_round").value);P._comp=comp>Pr?comp:0;
  const f=v=>"₺"+v.toFixed(2);
  $("p_final").textContent=f(Pr);
  bd.innerHTML="Maliyet (ürün+kargo): "+f(C)+"<br>"+(vatInc?("KDV: "+f(vatAmt)+"<br>"):"")+
    "Ödeme komisyonu: "+f(payAmt)+"<br>Platform/işlem: "+f(platAmt)+"<br>Reklam payı: "+f(adAmt)+"<br>İade/kayıp: "+f(retAmt)+"<br>"+
    "<span style='color:var(--ok)'>NET KÂR: "+f(net)+"  (%"+netPct.toFixed(1)+")</span>"+
    (P._comp?("<br>Karşılaştırma (üstü çizili): "+f(P._comp)):"")+
    (beRoas>0?("<br>Başabaş ROAS: "+beRoas.toFixed(2)+"x — reklamın bunun üstünde dönerse kârdasın"):"");
}
function applyPrice(){P.price=(P._final||0).toFixed(2);P.compare_at_price=P._comp?P._comp.toFixed(2):"";P.currency="TRY";toast("Fiyatlar uygulandı ✓");sync();}

/* ---- collect + preview ---- */
function collect(){
  P.title=$("f_title").value;P.description=$("f_desc").value;
  P.vendor=$("f_vendor").value;P.sku=$("f_sku").value;
}
function collectSeo(){
  P.seo={seo_title:$("s_title").value,meta_description:$("s_meta").value,handle:$("s_handle").value};
  P.tags=$("s_tags").value.split(",").map(s=>s.trim()).filter(Boolean);
}
function sync(){
  collect();collectSeo();
  $("v_title").textContent=P.title||"—";
  const sym={TRY:"₺",USD:"$",EUR:"€",GBP:"£"}[P.currency]||P.currency+" ";
  let ph=P.price?(sym+P.price):"—";
  if(P.compare_at_price)ph='<span style="text-decoration:line-through;color:var(--mute);font-size:15px;margin-right:8px">'+sym+P.compare_at_price+'</span>'+ph;
  $("v_price").innerHTML=ph;
  $("v_desc").textContent=P.description||"";
  const first=P.images.find(x=>x.use);
  const im=$("v_img");
  if(first){im.style.backgroundImage=`url("${first.src}")`;im.textContent="";}
  else{im.style.backgroundImage="none";im.textContent="görsel yok";}
}

/* ---- AI ---- */
async function ai(task,extra){
  collect();
  const body=Object.assign({task,title:P.title,description:P.description},extra||{});
  const r=await fetch("/api/ai",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const d=await r.json();
  if(!r.ok)throw new Error(d.error||"AI hatası");
  return d;
}
async function aiRewrite(){
  const b=$("rewriteBtn");b.disabled=true;b.textContent="✦ yazılıyor…";
  try{const d=await ai("rewrite",{tone:$("tone").value,lang:"Türkçe"});
    if(d.title)$("f_title").value=d.title;if(d.description)$("f_desc").value=d.description;
    sync();toast("Metin özgünleştirildi ✓");}
  catch(e){toast(e.message);}finally{b.disabled=false;b.textContent="✦ Başlık & açıklamayı yeniden yaz";}
}
async function aiTranslate(){
  const b=$("trBtn");b.disabled=true;
  try{const d=await ai("translate",{lang:$("tlang").value});
    if(d.title)$("f_title").value=d.title;if(d.description)$("f_desc").value=d.description;
    sync();toast("Çevrildi ✓");}
  catch(e){toast(e.message);}finally{b.disabled=false;}
}
async function aiSeo(){
  const b=$("seoBtn");b.disabled=true;b.textContent="✦ üretiliyor…";
  try{const d=await ai("seo",{lang:"Türkçe"});
    if(d.seo_title)$("s_title").value=d.seo_title;
    if(d.meta_description)$("s_meta").value=d.meta_description;
    if(d.handle)$("s_handle").value=d.handle;
    if(d.tags)$("s_tags").value=(d.tags||[]).join(", ");
    collectSeo();toast("SEO üretildi ✓");}
  catch(e){toast(e.message);}finally{b.disabled=false;b.textContent="✦ SEO üret";}
}
async function aiListing(){
  collect();
  const b=$("listingBtn");b.disabled=true;b.textContent="✦ oluşturuluyor… (biraz sürebilir)";
  try{
    const d=await ai("listing",{tone:$("tone").value,lang:"Türkçe",specs:P.specs,vendor:P.vendor,price:P.price,currency:P.currency});
    if(d.body_html){P.body_html=d.body_html;$("proPreview").innerHTML=d.body_html;$("proWrap").style.display="block";}
    if(d.seo_title)$("s_title").value=d.seo_title;
    if(d.meta_description)$("s_meta").value=d.meta_description;
    if(d.tags)$("s_tags").value=(d.tags||[]).join(", ");
    collectSeo();toast("Profesyonel listeleme hazır ✓");
    $("proWrap").scrollIntoView({behavior:"smooth",block:"nearest"});
  }catch(e){toast(e.message);}
  finally{b.disabled=false;b.textContent="✦ Profesyonel listeleme oluştur";}
}

/* ---- push ---- */
function setPubStatus(v,el){pubStatus=v;document.querySelectorAll("#statusSeg button").forEach(x=>x.classList.remove("on"));el.classList.add("on");}
async function doPush(){
  collect();collectSeo();
  const out={title:P.title,description:P.description,body_html:P.body_html||"",price:P.price,compare_at_price:P.compare_at_price||"",vendor:P.vendor,sku:P.sku,
    tags:P.tags,status:pubStatus,inventory:$("f_inv").value,seo:P.seo,
    images:P.images.filter(x=>x.use).map(x=>x.src)};
  if(!out.title)return toast("Başlık boş olamaz");
  const b=$("pushBtn");b.disabled=true;b.textContent="Gönderiliyor…";
  $("pushresult").innerHTML="";
  try{
    const r=await fetch("/api/push",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(out)});
    const d=await r.json();
    if(!r.ok){$("pushresult").innerHTML=`<span style="color:var(--coral)">✗ ${d.error}</span>`;return;}
    $("pushresult").innerHTML=`<span style="color:var(--ok)">✓ "${d.title}" mağazana eklendi</span>`+
      (d.admin_link?` — <a href="${d.admin_link}" target="_blank">Shopify'da aç →</a>`:"");
    toast("Ürün gönderildi ✓");
  }catch(e){$("pushresult").innerHTML=`<span style="color:var(--coral)">✗ ${e}</span>`;}
  finally{b.disabled=false;b.textContent="Mağazaya gönder ⤴";}
}

$("url").addEventListener("keydown",e=>{if(e.key==="Enter")doFetch();});
loadConfig();
</script>
</html>
"""

# ----------------------------- config -----------------------------
def load_config():
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    # config.json'da değer boşsa ortam değişkeninden doldur (host'ta kalıcılık için)
    env_map = {"shopify_store": "SHOPIFY_STORE", "shopify_token": "SHOPIFY_TOKEN",
               "shopify_client_id": "SHOPIFY_CLIENT_ID",
               "shopify_client_secret": "SHOPIFY_CLIENT_SECRET",
               "anthropic_key": "ANTHROPIC_API_KEY", "model": "ANTHROPIC_MODEL"}
    for key, env in env_map.items():
        if not cfg.get(key):
            cfg[key] = os.environ.get(env, cfg.get(key, ""))
    if not cfg.get("model"):
        cfg["model"] = DEFAULT_MODEL
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def norm_store(store):
    store = (store or "").strip().replace("https://", "").replace("http://", "").strip("/")
    if store and not store.endswith(".myshopify.com"):
        # kullanıcı sadece "magazam" yazdıysa
        if "." not in store:
            store = store + ".myshopify.com"
    return store


def get_shopify_token(cfg):
    """Doğrudan Admin API token varsa onu kullanır; yoksa Dev Dashboard'ın
    Client ID + Gizli anahtarıyla (client_credentials) taze bir token üretir.
    Bu token'lar 24 saat geçerli olduğu için her ihtiyaçta yeniden alınır."""
    token = cfg.get("shopify_token")
    if token:
        return token, None
    store = norm_store(cfg.get("shopify_store"))
    cid = cfg.get("shopify_client_id")
    csec = cfg.get("shopify_client_secret")
    if not (store and cid and csec):
        return None, "Shopify bilgileri eksik (mağaza + Client ID + Gizli anahtar)."
    try:
        r = requests.post(
            f"https://{store}/admin/oauth/access_token",
            data={"client_id": cid, "client_secret": csec,
                  "grant_type": "client_credentials"},
            headers={"Accept": "application/json"}, timeout=25)
    except Exception as e:
        return None, f"Token sunucusuna bağlanılamadı: {e}"
    if r.status_code != 200:
        return None, (f"Token alınamadı ({r.status_code}). "
                      "Client ID/gizli anahtarı ve uygulamanın mağazana KURULU olduğunu kontrol et. "
                      f"Ayrıntı: {r.text[:160]}")
    tok = r.json().get("access_token")
    if not tok:
        return None, "Shopify token döndürmedi."
    return tok, None


# ----------------------------- extraction -----------------------------
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def _clean_text(t):
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", t)
    t = _html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _num(v):
    if v is None:
        return ""
    s = str(v)
    s = re.sub(r"[^\d.,]", "", s)
    if s.count(",") and s.count("."):          # 1.299,90  -> 1299.90
        s = s.replace(".", "").replace(",", ".")
    elif s.count(","):                          # 349,90 -> 349.90
        s = s.replace(",", ".")
    return s


def _collect_jsonld(soup):
    out = []
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text() or ""
        try:
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict) and "@graph" in it and isinstance(it["@graph"], list):
                out.extend(it["@graph"])
            else:
                out.append(it)
    return out


def _find_product_node(nodes):
    for n in nodes:
        if not isinstance(n, dict):
            continue
        t = n.get("@type", "")
        types = t if isinstance(t, list) else [t]
        if any(str(x).lower() == "product" for x in types):
            return n
    return None


def parse_product(html_text, base_url):
    soup = BeautifulSoup(html_text, "html.parser")
    p = {"title": "", "price": "", "currency": "", "description": "",
         "images": [], "vendor": "", "sku": "", "tags": [], "specs": []}

    # 1) JSON-LD (en güvenilir)
    node = _find_product_node(_collect_jsonld(soup))
    if node:
        p["title"] = _clean_text(node.get("name", "")) or p["title"]
        p["description"] = _clean_text(node.get("description", "")) or p["description"]
        p["sku"] = str(node.get("sku", "") or "")
        brand = node.get("brand")
        if isinstance(brand, dict):
            p["vendor"] = brand.get("name", "") or ""
        elif isinstance(brand, str):
            p["vendor"] = brand
        img = node.get("image")
        if isinstance(img, str):
            p["images"].append(img)
        elif isinstance(img, list):
            for x in img:
                if isinstance(x, str):
                    p["images"].append(x)
                elif isinstance(x, dict) and x.get("url"):
                    p["images"].append(x["url"])
        offers = node.get("offers")
        off = offers[0] if isinstance(offers, list) and offers else offers
        if isinstance(off, dict):
            p["price"] = _num(off.get("price") or off.get("lowPrice"))
            p["currency"] = off.get("priceCurrency", "") or ""

    # 2) Open Graph / meta ile tamamla
    def meta(*keys):
        for k in keys:
            m = soup.find("meta", property=k) or soup.find("meta", attrs={"name": k})
            if m and m.get("content"):
                return m["content"].strip()
        return ""

    if not p["title"]:
        p["title"] = meta("og:title") or (soup.title.string.strip() if soup.title and soup.title.string else "")
    if not p["title"]:
        h1 = soup.find("h1")
        if h1:
            p["title"] = _clean_text(h1.get_text())
    if not p["description"]:
        p["description"] = _clean_text(meta("og:description", "description"))
    if not p["price"]:
        p["price"] = _num(meta("product:price:amount", "og:price:amount"))
    if not p["currency"]:
        p["currency"] = meta("product:price:currency", "og:price:currency")
    for m in soup.find_all("meta", property="og:image"):
        if m.get("content"):
            p["images"].append(m["content"])

    # görselleri temizle: mutlak yap + tekilleştir
    seen, imgs = set(), []
    for src in p["images"]:
        if not src:
            continue
        full = urljoin(base_url, src.strip())
        if full.startswith("http") and full not in seen:
            seen.add(full)
            imgs.append(full)
    p["images"] = imgs[:12]

    if not p["currency"]:
        p["currency"] = "TRY"
    p["source_url"] = base_url
    return p


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    url = (request.json or {}).get("url", "").strip()
    if not url.startswith("http"):
        return jsonify({"error": "Geçerli bir bağlantı gir (http/https ile başlamalı)."}), 400
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "tr,en;q=0.8"},
                         timeout=25)
        r.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"Sayfa çekilemedi: {e}"}), 502
    # charset'i doğru algıla (başlık yoksa içeriğe bak), Türkçe karakter bozulmasın
    if not r.encoding or r.encoding.lower() in ("iso-8859-1", "latin-1", "ascii"):
        r.encoding = r.apparent_encoding or "utf-8"
    product = parse_product(r.content, url)
    if not product["title"] and not product["images"]:
        return jsonify({"error": "Bu sayfada ürün bilgisi bulunamadı. Bağlantı bir ürün sayfası mı?"}), 422
    return jsonify(product)


# ----------------------------- AI -----------------------------
def call_claude(cfg, system, user_text, max_tokens=1500):
    key = cfg.get("anthropic_key")
    if not key:
        raise RuntimeError("Anthropic API anahtarı ayarlı değil (Ayarlar'dan gir).")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": cfg.get("model", DEFAULT_MODEL), "max_tokens": max_tokens,
              "system": system, "messages": [{"role": "user", "content": user_text}]},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Anthropic API hatası {r.status_code}: {r.text[:200]}")
    data = r.json()
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def parse_json_block(txt):
    t = txt.strip()
    t = re.sub(r"^```(json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    s, e = t.find("{"), t.rfind("}")
    if s >= 0 and e >= 0:
        t = t[s:e + 1]
    return json.loads(t)


AI_TASKS = {
    "rewrite": (
        "Sen bir e-ticaret metin yazarısın. Verilen ürün başlığı ve açıklamasını, aynı ürünü "
        "anlatan ama TAMAMEN ÖZGÜN, {tone} bir tonda, satışa yönelik yeni bir metne dönüştür. "
        "Kaynak metnin cümle yapısını kopyalama. Dili {lang}. SADECE JSON döndür: "
        '{{"title":"","description":""}}. description madde işaretleri içerebilir.'
    ),
    "seo": (
        "Sen bir Shopify SEO uzmanısın. Verilen ürün için SEO alanları üret. SADECE JSON döndür: "
        '{{"seo_title":"(max 60 karakter)","meta_description":"(max 155 karakter)",'
        '"tags":["5-8 etiket"],"handle":"url-uyumlu-slug"}}. Dil: {lang}.'
    ),
    "translate": (
        "Verilen başlık ve açıklamayı doğal, akıcı {lang} diline çevir. "
        'SADECE JSON döndür: {{"title":"","description":""}}.'
    ),
}


@app.route("/api/ai", methods=["POST"])
def api_ai():
    body = request.json or {}
    task = body.get("task")
    cfg = load_config()
    lang = body.get("lang", "Türkçe")

    # --- Profesyonel, güven veren tam ürün sayfası üret ---
    if task == "listing":
        store = cfg.get("store_name") or "mağazamız"
        guarantee = cfg.get("trust_guarantee") or "Kalite garantisi"
        shipping = cfg.get("trust_shipping") or "Hızlı ve takipli kargo"
        returns = cfg.get("trust_returns") or "14 gün içinde kolay iade"
        payment = cfg.get("trust_payment") or "SSL ile güvenli ödeme"
        system = (
            "Sen üst düzey bir e-ticaret ürün sayfası editörüsün. Verilen ham ürün bilgisinden GÜVEN VEREN, "
            "PROFESYONEL bir Shopify ürün açıklaması üret. Çıktı, HER temada düzgün görünecek biçimde SADECE "
            "satır-içi (inline style) stilli TEMİZ HTML olsun; harici CSS veya <script> KULLANMA. "
            "Şu bölümleri sırayla üret: "
            "(1) 2-3 cümlelik dikkat çekici giriş; "
            "(2) 'Öne Çıkan Faydalar' başlıklı 4-6 maddelik liste; "
            "(3) 'Nasıl Kullanılır' 3-4 kısa adım; "
            "(4) 'Ürün Özellikleri' iki sütunlu bir tablo; "
            "(5) bir GÜVEN ŞERİDİ: yan yana 4 kutu — "
            f"🛡️ Garanti: {guarantee} · 🚚 Kargo: {shipping} · ↩️ İade: {returns} · 🔒 {payment}; "
            "(6) 'Sıkça Sorulan Sorular' başlığı altında 5 adet soru-cevap. "
            "Yazı dili: " + lang + ". Marka: " + store + ". "
            "Renkleri sade ve şık tut (koyu metin, ince gri çizgiler, yumuşak arka plan kutuları). "
            "ABARTMA: sağlık, kesin sonuç veya yanıltıcı vaat verme. "
            'SADECE şu JSON formatında yanıt ver, başka hiçbir metin yazma: '
            '{"body_html":"...","seo_title":"(max 60 karakter)","meta_description":"(max 155 karakter)","tags":["5-8 etiket"]}'
        )
        product = {
            "title": body.get("title", ""), "description": body.get("description", ""),
            "specs": body.get("specs", []), "vendor": body.get("vendor", ""),
            "price": body.get("price", ""), "currency": body.get("currency", "TRY"),
        }
        try:
            out = call_claude(cfg, system, json.dumps(product, ensure_ascii=False), max_tokens=3800)
            return jsonify(parse_json_block(out))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if task not in AI_TASKS:
        return jsonify({"error": "Bilinmeyen görev."}), 400
    tone = body.get("tone", "satış odaklı")
    system = AI_TASKS[task].format(tone=tone, lang=lang)
    payload = json.dumps({"title": body.get("title", ""),
                          "description": body.get("description", "")}, ensure_ascii=False)
    try:
        out = call_claude(cfg, system, payload, max_tokens=1500)
        return jsonify(parse_json_block(out))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------- Shopify push -----------------------------
def shopify_graphql(store, token, query, variables=None):
    return requests.post(
        f"https://{store}/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}}, timeout=40)


def desc_html(product):
    lines = [l for l in (product.get("description") or "").split("\n") if l.strip()]
    html = "".join(f"<p>{_html.escape(l)}</p>" for l in lines)
    specs = [s for s in product.get("specs", []) if s.get("name")]
    if specs:
        html += "<ul>" + "".join(
            f"<li><strong>{_html.escape(s['name'])}:</strong> {_html.escape(str(s.get('value','')))}</li>"
            for s in specs) + "</ul>"
    return html or "<p></p>"


@app.route("/api/push", methods=["POST"])
def api_push():
    cfg = load_config()
    store = norm_store(cfg.get("shopify_store"))
    token, err = get_shopify_token(cfg)
    if not store or not token:
        return jsonify({"error": err or "Shopify bağlantısı ayarlı değil (Ayarlar'dan gir)."}), 400

    product = request.json or {}
    body_html = product.get("body_html") or desc_html(product)
    status = "ACTIVE" if product.get("status") == "active" else "DRAFT"
    meta = product.get("seo") or {}

    # 1) ürünü oluştur (GraphQL Admin API)
    create_q = """
    mutation productCreate($input: ProductInput!) {
      productCreate(input: $input) {
        product { id title variants(first: 1) { edges { node { id } } } }
        userErrors { field message }
      }
    }"""
    pinput = {
        "title": product.get("title") or "Adsız ürün",
        "descriptionHtml": body_html,
        "vendor": product.get("vendor", "") or "",
        "status": status,
    }
    if product.get("tags"):
        pinput["tags"] = product["tags"]
    if meta.get("seo_title") or meta.get("meta_description"):
        pinput["seo"] = {"title": meta.get("seo_title", ""),
                         "description": meta.get("meta_description", "")}
    if meta.get("handle"):
        pinput["handle"] = meta["handle"]

    try:
        r = shopify_graphql(store, token, create_q, {"input": pinput})
    except Exception as e:
        return jsonify({"error": f"Shopify'a bağlanılamadı: {e}"}), 502
    if r.status_code == 401:
        return jsonify({"error": "401 — token reddedildi. Uygulamanın mağazana KURULU ve "
                                 "'write_products' izninin ekli olduğundan emin ol."}), 400
    if r.status_code != 200:
        return jsonify({"error": f"Shopify {r.status_code}: {r.text[:200]}"}), 400
    jr = r.json()
    if jr.get("errors"):
        return jsonify({"error": str(jr["errors"])[:250]}), 400
    pc = jr.get("data", {}).get("productCreate", {})
    if pc.get("userErrors"):
        return jsonify({"error": "; ".join(u["message"] for u in pc["userErrors"])}), 400
    prod = pc.get("product") or {}
    pid = prod.get("id")
    if not pid:
        return jsonify({"error": "Ürün oluşturulamadı (kimlik dönmedi)."}), 400
    edges = prod.get("variants", {}).get("edges", [])
    variant_id = edges[0]["node"]["id"] if edges else None

    # 2) fiyat + karşılaştırma fiyatı + SKU
    if variant_id:
        vin = {"id": variant_id, "price": str(product.get("price") or "0.00")}
        if product.get("compare_at_price"):
            vin["compareAtPrice"] = str(product["compare_at_price"])
        if product.get("sku"):
            vin["inventoryItem"] = {"sku": product["sku"]}
        vq = """
        mutation vbu($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            userErrors { field message }
          }
        }"""
        try:
            shopify_graphql(store, token, vq, {"productId": pid, "variants": [vin]})
        except Exception:
            pass

    # 3) görseller (URL'den)
    imgs = [s for s in product.get("images", []) if s]
    if imgs:
        mq = """
        mutation cm($productId: ID!, $media: [CreateMediaInput!]!) {
          productCreateMedia(productId: $productId, media: $media) {
            mediaUserErrors { field message }
          }
        }"""
        media = [{"originalSource": s, "mediaContentType": "IMAGE"} for s in imgs]
        try:
            shopify_graphql(store, token, mq, {"productId": pid, "media": media})
        except Exception:
            pass

    numeric_id = pid.split("/")[-1]
    shop_name = store.replace(".myshopify.com", "")
    admin_link = f"https://admin.shopify.com/store/{shop_name}/products/{numeric_id}"
    return jsonify({"ok": True, "id": numeric_id, "admin_link": admin_link,
                    "title": prod.get("title", "")})


# ----------------------------- settings & test -----------------------------
@app.route("/api/config", methods=["GET"])
def api_config():
    cfg = load_config()
    return jsonify({
        "shopify_ready": bool(norm_store(cfg.get("shopify_store")) and (
            cfg.get("shopify_token") or (cfg.get("shopify_client_id") and cfg.get("shopify_client_secret")))),
        "ai_ready": bool(cfg.get("anthropic_key")),
        "shopify_store": cfg.get("shopify_store", ""),
        "shopify_client_id": cfg.get("shopify_client_id", ""),
        "model": cfg.get("model", DEFAULT_MODEL),
        "store_name": cfg.get("store_name", ""),
        "trust_guarantee": cfg.get("trust_guarantee", ""),
        "trust_shipping": cfg.get("trust_shipping", ""),
        "trust_returns": cfg.get("trust_returns", ""),
        "trust_payment": cfg.get("trust_payment", ""),
    })


@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.json or {}
    cfg = load_config()
    for k in ["shopify_store", "shopify_token", "shopify_client_id", "shopify_client_secret",
              "anthropic_key", "model",
              "store_name", "trust_guarantee", "trust_shipping", "trust_returns", "trust_payment"]:
        if k in data and str(data[k]).strip() != "":
            cfg[k] = str(data[k]).strip()
        elif data.get(k) == "__CLEAR__":
            cfg[k] = ""
    save_config(cfg)
    return jsonify({"ok": True})


@app.route("/api/test-shopify", methods=["POST"])
def api_test_shopify():
    cfg = load_config()
    store = norm_store(cfg.get("shopify_store"))
    token, err = get_shopify_token(cfg)
    if not store or not token:
        return jsonify({"ok": False, "error": err or "Mağaza adı veya kimlik bilgisi eksik."})
    try:
        r = shopify_graphql(store, token, "{ shop { name } }")
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
    if r.status_code == 401:
        return jsonify({"ok": False, "error": "401 — token reddedildi. Uygulama mağazana KURULU mu ve "
                                              "'write_products' izni ekli mi? Kontrol et."})
    if r.status_code != 200:
        return jsonify({"ok": False, "error": f"Shopify {r.status_code}: {r.text[:160]}"})
    jr = r.json()
    if jr.get("errors"):
        return jsonify({"ok": False, "error": str(jr["errors"])[:180]})
    name = (jr.get("data", {}).get("shop") or {}).get("name", store)
    return jsonify({"ok": True, "name": name})


# ----------------------------- erişim koruması -----------------------------
# Siteyi yayınladığında herkes girip mağazana ürün göndermesin diye:
# host'ta ACCESS_PASSWORD ortam değişkenini ayarla → site parola ister.
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "")


@app.before_request
def _gate():
    if not ACCESS_PASSWORD:
        return  # parola ayarlı değilse koruma kapalı (yerel kullanım)
    auth = request.authorization
    if not auth or auth.password != ACCESS_PASSWORD:
        from flask import Response
        return Response("Giris gerekli", 401,
                        {"WWW-Authenticate": 'Basic realm="Import Konsolu"'})


# ----------------------------- arayüz -----------------------------
@app.route("/")
def index():
    return LANDING


@app.route("/konsol")
def konsol():
    return HTML


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print("\n  Import Konsolu calisiyor  ->  http://localhost:%d\n" % port)
    app.run(host="0.0.0.0", port=port, debug=False)
