import os
import json
import asyncio
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

ARQUIVO_CANAIS = "canais.json"
ARQUIVO_ESTADO = "ultimo_video.json"


def carregar_json(arquivo):
    try:
        with open(arquivo, "r") as f:
            return json.load(f)
    except:
        return {}


def salvar_json(arquivo, dados):
    with open(arquivo, "w") as f:
        json.dump(dados, f, indent=4)


def buscar_canal(link):
    username = link.rstrip("/").split("/")[-1].replace("@", "")

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": username,
        "type": "channel",
        "maxResults": 1,
        "key": YOUTUBE_API_KEY
    }

    r = requests.get(url, params=params).json()

    if "items" not in r or len(r["items"]) == 0:
        return None

    canal = r["items"][0]

    return {
        "nome": canal["snippet"]["title"],
        "id": canal["id"]["channelId"]
    }


def ultimo_video(channel_id):
    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": YOUTUBE_API_KEY,
        "channelId": channel_id,
        "part": "snippet,id",
        "order": "date",
        "maxResults": 1
    }

    r = requests.get(url, params=params).json()

    if "items" not in r or len(r["items"]) == 0:
        return None

    video = r["items"][0]

    if video["id"]["kind"] != "youtube#video":
        return None

    return {
        "id": video["id"]["videoId"],
        "titulo": video["snippet"]["title"],
        "link": f"https://youtu.be/{video['id']['videoId']}"
    }


async def monitorar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text(
            "Uso:\n/monitorar https://youtube.com/@canal"
        )
        return

    link = context.args[0]

    canal = buscar_canal(link)

    if not canal:
        await update.message.reply_text("Canal não encontrado.")
        return

    canais = carregar_json(ARQUIVO_CANAIS)

    canais[canal["id"]] = {
        "nome": canal["nome"],
        "link": link
    }

    salvar_json(ARQUIVO_CANAIS, canais)

    await update.message.reply_text(
        f"✅ Canal adicionado:\n\n{canal['nome']}"
    )


async def canais(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dados = carregar_json(ARQUIVO_CANAIS)

    if not dados:
        await update.message.reply_text(
            "Nenhum canal monitorado."
        )
        return

    texto = "📺 Canais monitorados:\n\n"

    for canal in dados.values():
        texto += f"• {canal['nome']}\n"

    await update.message.reply_text(texto)


async def remover(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text(
            "Uso:\n/remover nome_do_canal"
        )
        return

    nome = " ".join(context.args).lower()

    canais = carregar_json(ARQUIVO_CANAIS)

    remover_id = None

    for canal_id, canal in canais.items():
        if nome in canal["nome"].lower():
            remover_id = canal_id
            break

    if not remover_id:
        await update.message.reply_text("Canal não encontrado.")
        return

    nome_canal = canais[remover_id]["nome"]

    del canais[remover_id]

    salvar_json(ARQUIVO_CANAIS, canais)

    await update.message.reply_text(
        f"🗑 Canal removido:\n\n{nome_canal}"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    canais = carregar_json(ARQUIVO_CANAIS)

    await update.message.reply_text(
        f"✅ Bot online\n📺 Canais monitorados: {len(canais)}"
    )


async def verificar_videos(app):

    while True:

        try:

            canais = carregar_json(ARQUIVO_CANAIS)
            estado = carregar_json(ARQUIVO_ESTADO)

            for canal_id, canal in canais.items():

                video = ultimo_video(canal_id)

                if not video:
                    continue

                if canal_id not in estado:
                    estado[canal_id] = video["id"]
                    salvar_json(ARQUIVO_ESTADO, estado)
                    continue

                if estado[canal_id] != video["id"]:

                    mensagem = (
                        f"📹 Novo vídeo publicado\n\n"
                        f"📺 Canal: {canal['nome']}\n\n"
                        f"📝 {video['titulo']}\n\n"
                        f"🔗 {video['link']}"
                    )

                    await app.bot.send_message(
                        chat_id=os.getenv("CHAT_ID"),
                        text=mensagem
                    )

                    estado[canal_id] = video["id"]

                    salvar_json(
                        ARQUIVO_ESTADO,
                        estado
                    )

            await asyncio.sleep(300)

        except Exception as e:
            print("ERRO:", e)
            await asyncio.sleep(60)


async def iniciar_background(app):

    asyncio.create_task(
        verificar_videos(app)
    )


def main():

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("monitorar", monitorar)
    )

    app.add_handler(
        CommandHandler("canais", canais)
    )

    app.add_handler(
        CommandHandler("remover", remover)
    )

    app.add_handler(
        CommandHandler("status", status)
    )

    app.post_init = iniciar_background

    app.run_polling()


if __name__ == "__main__":
    main()
