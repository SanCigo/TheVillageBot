import random as R
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
import telegram
import logging
from telegram.ext import Updater, PicklePersistence, MessageHandler, CommandHandler, ConversationHandler, \
    CallbackQueryHandler, Filters
import time
from functools import wraps
import json
import os

if not telegram.__version__.startswith("13."):
    print("This bot only runs on 13.x version of the library. 13.15 reccomended.")
    exit()


script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)


# put the token in the same path inside a text file
with open("token.txt", "r") as f:
    TOKEN = f.read()

# bot admins
with open("admins.txt", "r") as f:
    ADMINS = [int(i) for i in f.readlines()]  # list of telegram ids separated by newline

my_persistence = PicklePersistence("balance.pickle")
updater = Updater(token=TOKEN,
                  use_context=True,
                  persistence=my_persistence)
dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
R.seed()

with open("ruoli.json", "r") as f:
    ruoli = json.load(f)
lupi = ["Lupo", "Lupo Alfa", "Cucciolo di Lupo", "Licantropo", "Lupo delle Nevi"]
vs = {"village": ["Contadino", "Massone", "Veggente", "Apprendista Veggente", "UomoLupo", "Ubriaco", "Maledetto",
                  "Prostituta", "Osservatore", "Artigliere", "Traditore",
                  "Angelo Custode", "Cacciatore di Satanisti", "Bambino Ribelle", "Folle", "Cupido",
                  "Cacciatore Urbano", "Sindaco", "Principe", "Fabbro", "Morfeo", "Oracolo", "Pacifista",
                  "Vecchio Saggio", "Guastafeste", "Chimico", "Becchino", "Augure", "Investigatore", "Goffo", "Sosia"],
      "!village": ["Lupo", "Lupo Alfa", "Cucciolo di Lupo", "Licantropo", "Lupo delle Nevi", "Stregone",
                   "Serial Killer", "Masochista", "Satanista", "Ladro", "Piromane"]}
not_convertible_roles = ["Veggente", "Angelo Custode", "Investigatore", "Maledetto", "Prostituta", "Cacciatore Urbano",
                         "Sosia", "Lupo", "Lupo Alfa", "Cucciolo di Lupo", "Licantropo",
                         "Lupo delle Nevi", "Serial Killer", "Ladro"]


def build_menu(buttons,
               n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(update, context, *args, **kwargs)

    return wrapped


GET = range(1)
ASK_ROLE, GET_ANSWER = range(2)


@restricted
def stats(update, context):
    buttons = [InlineKeyboardButton("👤 Utenti", callback_data="p"),
               InlineKeyboardButton("👥 Gruppi", callback_data="g")]
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
    update.message.reply_markdown("*Seleziona una categoria*", reply_markup=reply_markup)
    return GET


def get_stats(update, context):
    mex = ""
    c = 0
    if update.callback_query.data == "p":
        for user_id, start_time in context.bot_data["stats"]["users"]["ids"].items():
            c += 1
            mex += "[Utente " + str(c) + "](tg://user?id=" + str(user_id) + ") | " + start_time + "\n"
        mex += "*" + str(c) + "* utenti hanno avviato il tuo bot."
        buttons = [InlineKeyboardButton("👥 Gruppi", callback_data="g")]
    elif context.bot_data["stats"]["groups"]["names"]:
        for group_name, start_time in context.bot_data["stats"]["groups"]["names"]:
            c += 1
            mex += "*" + group_name + "*: " + start_time + "\n"
        mex += "*" + str(c) + "* gruppi hanno aggiunto ed avviato il tuo bot."
        buttons = [InlineKeyboardButton("👤 Utenti", callback_data="p")]
    else:
        update.callback_query.answer("Nessun gruppo ha aggiunto il bot.")
        return GET
    update.callback_query.answer()
    buttons.append(InlineKeyboardButton("❌ Chiudi", callback_data="fb"))
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
    context.bot.edit_message_text(text=mex,
                                  chat_id=update.effective_chat.id,
                                  message_id=update.callback_query.message.message_id,
                                  reply_markup=reply_markup,
                                  parse_mode=ParseMode.MARKDOWN)
    return GET


'''------------------------ FRONTEND inizia qui --------------------------'''


def start(update, context):
    # Registra ogni utente ed ogni gruppo a cui viene aggiunto e inviato /start (ATTENZIONE: RICHIEDE persistence)
    if "stats" in context.bot_data:
        if update.effective_chat.type == "private" and update.effective_chat.id not in \
                context.bot_data["stats"]["users"]["ids"]:  # Chat privata
            context.bot_data["stats"]["users"]["ids"][update.effective_chat.id] = time.ctime(time.time())
        elif update.effective_chat.type != 'channel' and update.effective_chat.id not in \
                context.bot_data["stats"]["groups"]["ids"]:
            context.bot_data["stats"]["groups"]["names"][update.effective_chat.title] = time.ctime(time.time())
            context.bot_data["stats"]["groups"]["ids"].add(update.effective_chat.id)
    else:
        context.bot_data["stats"] = {}
        context.bot_data["stats"]["users"] = {}
        context.bot_data["stats"]["groups"] = {}
        context.bot_data["stats"]["users"]["ids"] = {}
        context.bot_data["stats"]["groups"]["ids"] = set()
        context.bot_data["stats"]["groups"]["names"] = {}
        start(update, context)
        return
    # Fine blocco
    update.message.reply_markdown("Inviami il numero di player e ti fornisco un game bilanciato.\n"
                                  "Per le altre funzioni, usa il menù comandi.\nCreato da @SanCigo\n*Source:* "
                                  "https://github.com/GreyWolfDev/Werewolf")


def generate(update, context):
    if update.message.text[-1].isdigit():
        playerCount = int(update.message.text)
        no_index = False
    else:
        playerCount = int(update.message.text[:-1])
        no_index = True
    if 5 <= playerCount <= 35:
        output = Balance(playerCount)
        context.user_data["current"] = output[0]
        indice = 1
        if no_index:
            mex = "```\n"
        else:
            mex = ''
        for ruolo in output[0]:
            if no_index:
                mex += ruolo + "\n"
            else:
                mex += str(indice) + ". " + ruolo + "\n"
                indice += 1
        if no_index:
            mex += "```"
        mex += "\n" + "*Villaggio:* " + output[1] + "\n*Nemici:* " + output[2] + "\n*Differenza massima:* " + output[3]
        update.message.reply_markdown(mex)
    else:
        update.message.reply_markdown("Il numero di giocatori deve essere *minimo 5* e *massimo 35*.")


def custom_game(update, context):
    text = update.message.text
    rolesToAssign = text.split("\n")
    context.user_data["current"] = rolesToAssign
    playerCount = len(rolesToAssign)
    if playerCount < 5:
        update.message.reply_markdown("Una partita è composta da almeno *5 giocatori*.\nSe stavi facendo un quiz, "
                                      "potrebbe essere passato troppo tempo. Puoi iniziarne un altro con /quiz")
        return
    v_s = 0
    nv_s = 0
    for role in rolesToAssign:
        splitter = role.find(".")
        if splitter == -1:
            if role not in vs["village"]:
                try:
                    nv_s += GetStrenght(role, rolesToAssign, playerCount)
                except TypeError:
                    update.message.reply_markdown("Per uno o più ruoli personalizzati inviati *manca l'indicazione del "
                                                  "team.*")
                    return
            else:
                v_s += GetStrenght(role, rolesToAssign, playerCount)
        else:
            try:
                if role[-1] == "b":
                    v_s += int(role[splitter + 1:-1])
                elif role[-1] == "c":
                    nv_s += int(role[splitter + 1:-1])
                else:
                    update.message.reply_markdown("Per uno o più ruoli personalizzati inviati *manca l'indicazione del "
                                                  "team.*")
                    return
            except ValueError:
                update.message.reply_markdown("Per uno o più ruoli personalizzati inviati *manca l'indicazione del "
                                              "valore di bilancio.*")
                return
    max_difference = (playerCount / 4) + 1
    if abs(v_s - nv_s) > max_difference:
        update.message.reply_markdown("*Il game non è bilanciato.*\n*Villaggio:* " + str(v_s) + "\n*Nemici:* " +
                                      str(nv_s) + "\n*Differenza:* " + str(abs(v_s - nv_s)) +
                                      "\n*Differenza massima:* " + str(max_difference))
    else:
        update.message.reply_markdown("*Il game è bilanciato.*\n*Villaggio:* " + str(v_s) + "\n*Nemici:* " +
                                      str(nv_s) + "\n*Differenza:* " + str(abs(v_s - nv_s)) +
                                      "\n*Differenza massima:* " + str(max_difference))


def useful_links(update, context):
    update.message.reply_markdown("*CE SO I LINK*\n"
                                  "[Bilancio di gioco](https://telegra.ph/Bilancio-del-gioco-08-09)\n"
                                  "[Conversione Satanisti](https://telegra.ph/Percentuali-conversione-03-11)\n"
                                  "[Lista ruoli](https://telegra.ph/Ruoli-e-Team-06-05)", disable_web_page_preview=True)


def random(update, context):
    conv = ["convertito", "fede alta"]
    events = {"satan": {}, "kill_other": {}}
    """SATAN EVENTS"""

    events["satan"]["👳 Veggente"] = R.choices(conv, [0.4, 0.6])
    events["satan"]["🕵️ Investigatore"] = R.choices(conv, [0.7, 0.3])
    events["satan"]["😾 Maledetto"] = R.choices(conv, [0.6, 0.4])
    events["satan"]["⚒ Fabbro"] = R.choices(conv, [0.75, 0.25])
    events["satan"]["🦅 Augure"] = R.choices(conv, [0.4, 0.6])
    events["satan"]["📚 Vecchio Saggio"] = R.choices(conv, [0.3, 0.7])
    events["satan"]["💤 Morfeo"] = R.choices(conv, [0.6, 0.4])
    events["satan"]["🌀 Oracolo"] = R.choices(conv, [0.5, 0.5])
    events["satan"]["☮️ Pacifista"] = R.choices(conv, [0.8, 0.2])
    events["satan"]["🔮 Stregone"] = R.choices(conv, [0.4, 0.6])
    events["satan"]["💋 Prostituta"] = R.choices(conv, [0.7, 0.3])
    events["satan"]["👼 Angelo Custode"] = R.choices(conv, [0.6, 0.4])
    if R.choices(conv, [0.5, 0.5]) == [conv[1]]:
        events["satan"]["🎯 Cacciatore"] = R.choices(["uccide il satanista", conv[1]], [0.25, 0.75])
    else:
        events["satan"]["🎯 Cacciatore"] = conv

    """KILL & OTHER EVENTS"""
    events["kill_other"]["👼 da 🐺"] = R.choices(["Lupo protetto", "💀 Angelo"], [0.5, 0.5])
    events["kill_other"]["🐺 vs 🔪"] = R.choices(["💀 Lupo", "💀 Serial Killer"], [0.8, 0.2])
    events["kill_other"]["🐺 vs 🎯"] = R.choices(["💀 Lupo", "💀 Cacciatore Urbano"], [0.3, 0.7])
    events["kill_other"]["🐺🐺 vs 🎯"] = R.choices(["💀 Lupo, Cacciatore Urbano", "💀 Cacciatore Urbano"], [0.5, 0.5])
    events["kill_other"]["🐺🐺🐺 vs 🎯"] = R.choices(["💀 Lupo, Cacciatore Urbano", "💀 Cacciatore Urbano"], [0.7, 0.3])
    events["kill_other"]["🐺🐺🐺🐺 vs 🎯"] = R.choices(["💀 Lupo, Cacciatore Urbano", "💀 Cacciatore Urbano"], [0.9, 0.1])
    events["kill_other"]["⚡️ infetta?"] = R.choices(["Sì", "No"], [0.2, 0.8])
    events["kill_other"]["🕵️ scoperto?"] = R.choices(["Sì", "No"], [0.4, 0.6])
    events["kill_other"]["👨‍🔬 vs 🧑"] = R.choices(["💀 Chimico", "vince Chimico"], [0.5, 0.5])
    events["kill_other"]["😈 ruba?"] = R.choices(["Sì", "No"], [0.5, 0.5])
    if context.args and int(context.args[0]) < 35:
        events["kill_other"]["🤕 goffa?"] = R.choices(["Sì - " + str(R.randint(1, int(context.args[0]) - 1)), "No"], [0.5, 0.5])
        events["kill_other"]["🌀 Oracolo"] = [str((R.randint(1, int(context.args[0]) - 1)))]
    """COMPOSIZIONE STRINGA"""
    mex = "<b>CONVERSIONE SATAN:</b>\n<b>☠️ Becchino:</b> 30%*\n"
    for role, event in events["satan"].items():
        mex += "<b>" + role + ":</b> " + event[0] + "\n"
    mex += "\n<b>ALTRO:</b>\n"
    for role, event in events["kill_other"].items():
        mex += "<b>" + role + ":</b> " + event[0] + "\n"
    mex += "\n*la probabilità del Becchino vale solamente nel caso non scavasse, e con essa " \
           "è presente la proabilità del Satanista di cadere nella tomba."
    update.message.reply_html(mex)


def becchino(update, context):
    tombe = int(context.args[0])
    n_baddies = int(context.args[1])
    n_goodies = int(context.args[2])
    chance_baddies = (20 + (30 - (30*(0.5**(tombe - 1)))))/100
    chance_goodies = chance_baddies/2
    mex = ""
    for i in range(n_baddies):
        mex += "*Nemico " + str(i+1) + ":* " + R.choices(["☠️", "❌"],
                                                       [chance_baddies, 1 - chance_baddies])[0] + "\n"
    for i in range(n_goodies):
        mex += "*Amico " + str(i+1) + ":* " + R.choices(["☠️", "❌"],
                                                       [chance_goodies, 1 - chance_goodies])[0] + "\n"
    mex += R.choices(["🔪\n", ""], [chance_goodies, 1 - chance_goodies])[0]
    for i in range(2):
        mex += R.choices(["🐺 " + str(i+1) + "\n", ""], [chance_goodies, 1 - chance_goodies])[0]
    update.message.reply_markdown(mex)


def randomint(update, context):
    update.message.reply_text(str(R.randint(1, int(context.args[0]))))


def priority(update, context):
    update.message.reply_photo("https://i.imgur.com/BSJMWK3.png")


def check(update, context):
    if not context.args:
        update.message.reply_text("Specifica un ruolo.")
    else:
        update.message.reply_text(GetStrenght(update.message.text[7:], rolesToAssign=[], playerCount=1))


def quiz(update, context):
    buttons = [InlineKeyboardButton("▶️ Inizia!", callback_data="get"),
               InlineKeyboardButton("❌ Annulla", callback_data="exit")]
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    update.message.reply_markdown("ℹ️ *Perché un quiz?*\nA differenza del canonico Lupus in Fabula, in questa "
                                  "versione il bluff è basato totalmente sul fingersi altri ruoli. Pertanto, "
                                  "è di primaria importanza conoscere al meglio tutti i ruoli presenti all'interno "
                                  "del gioco.\n\n❓ *Come funziona*\nPer iniziare, *premi il pulsante qui sotto!*",
                                  reply_markup=reply_markup)
    return ASK_ROLE


def ask_role(update, context):
    chosen = "."
    if "chosen" not in context.user_data:
        context.user_data["chosen"] = ["."]
    if "counter" not in context.user_data:
        context.user_data["counter"] = 0
    elif context.user_data["counter"] == 39:
        # Una volta indovinati tutti i ruoli, la lista dei ruoli scelti si resetta.
        # Se ci sono problemi, provare ad abbassare il contatore (oppure scoprire perché funziona male, ma tu, me
        # del futuro, sono sicuro sarai troppo pigro per farlo.
        context.user_data["counter"] = 0
        context.user_data["chosen"] = ["."]
    while chosen.casefold() in context.user_data["chosen"] or not ruoli[chosen]:
        chosen = R.choice(list(ruoli.keys()))
    if update.message or update.callback_query.data == "skip":
        context.user_data["old_role"] = context.user_data["role"]
    context.user_data["role"] = chosen.casefold()
    text = "❓ <b>Che ruolo è?</b>\n" + ruoli[chosen]
    buttons = [InlineKeyboardButton("⏩ Salta", callback_data="skip"),
               InlineKeyboardButton("❌ Annulla", callback_data="exit")]
    reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
    if update.callback_query:
        if update.callback_query.data == "skip":
            update.callback_query.answer("La risposta era " + context.user_data["old_role"].capitalize() + "!")
        else:
            update.callback_query.answer()
        context.bot.edit_message_text(text=text,
                                      chat_id=update.effective_chat.id,
                                      message_id=update.callback_query.message.message_id,
                                      reply_markup=reply_markup,
                                      parse_mode=ParseMode.HTML)
        context.user_data["skip_from_slash"] = update.callback_query.message.message_id
    else:
        context.bot.edit_message_text(text="La risposta era *" + context.user_data["old_role"].capitalize() + "*!",
                                      chat_id=update.effective_chat.id,
                                      message_id=context.user_data["skip_from_slash"],
                                      parse_mode=ParseMode.MARKDOWN)
        mex_id = update.message.reply_html(text, reply_markup=reply_markup).message_id
        context.user_data["skip_from_slash"] = mex_id
    return GET_ANSWER


def checkAnswer(update, context):
    answer = update.message.text.casefold()
    if answer.endswith("."):
        answer = answer.replace(".", "")
    if answer == context.user_data["role"]:
        buttons = [InlineKeyboardButton("➡️ Avanti", callback_data="get"),
                   InlineKeyboardButton("❌ Annulla", callback_data="exit")]
        reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
        context.user_data["chosen"].append(context.user_data["role"])
        context.user_data["counter"] += 1
        update.message.reply_markdown(
            "✅ *Complimenti!* Hai indovinato. Se vuoi continuare, premi il pulsante qui sotto.",
            reply_markup=reply_markup)
        return ASK_ROLE
    elif answer in context.user_data["role"] or context.user_data["role"] in answer:
        update.message.reply_markdown("*Fuochino...*\nControlla di aver scritto correttamente il nome del ruolo")
    else:
        update.message.reply_markdown(
            "*Sbagliato, riprova!*\nSe vuoi saltare questo ruolo, premi il pulsante sopra oppure usa /skip")
    return GET_ANSWER


def end(update, context):
    if update.callback_query.data == "exit":
        mex = "❌ *Annullato con successo.*\nSe vuoi rigiocare, usa semplicemente /quiz"
    else:
        mex = "❌ *Annullato*"
    context.bot.edit_message_text(text=mex,
                                  chat_id=update.effective_chat.id,
                                  message_id=update.callback_query.message.message_id,
                                  parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


'''------------------------ BACKEND inizia qui --------------------------'''


def Get_RoleList(playerCount):
    possibleWolves = list(lupi)
    rolesToAssign = []
    wolftoadd = possibleWolves[R.randint(0, 4)]
    i = 0
    while i < min(max(playerCount / 5, 1), 5):
        rolesToAssign.append(wolftoadd)
        if wolftoadd != "Lupo":
            possibleWolves.remove(wolftoadd)
        wolftoadd = possibleWolves[R.randint(0, len(possibleWolves) - 1)]
        i += 1
    if len(rolesToAssign) == 1 and rolesToAssign[0] == "Lupo delle Nevi":
        rolesToAssign[0] == "Lupo"
    for role in list(ruoli.keys()):
        if role in lupi:
            pass
        elif "atan" in role:
            if playerCount > 10:
                rolesToAssign.append(role)
        else:
            rolesToAssign.append(role)
    rolesToAssign.append("Massone")
    rolesToAssign.append("Massone")
    if "Satanista" in rolesToAssign:
        rolesToAssign.append("Satanista")
        rolesToAssign.append("Satanista")
    i = 0
    while i < playerCount / 4:
        i += 1
        rolesToAssign.append("Contadino")
    return rolesToAssign


def Balance(playerCount):
    balance = False
    while not balance:
        rolesToAssign = Get_RoleList(playerCount)
        R.shuffle(rolesToAssign)
        rolesToAssign = rolesToAssign[:playerCount]
        if "Apprendista Veggente" in rolesToAssign and "Veggente" not in rolesToAssign:
            index = rolesToAssign.index("Apprendista Veggente")
            rolesToAssign[index] = "Veggente"
        if "Satanista" in rolesToAssign and "Cacciatore di Satanisti" not in rolesToAssign:
            try:
                rolesToAssign[rolesToAssign.index("Contadino")] = "Cacciatore di Satanisti"
            except ValueError:
                continue
        for index, role in enumerate(rolesToAssign):
            if role in ("Stregone", "Traditore", "Lupo delle Nevi") and not any(
                    i in rolesToAssign for i in lupi[:3]):
                r_index = R.randint(0, len(lupi) - 2)
                rolesToAssign[index] = lupi[r_index]
        balance, v_n, v_s, nv_n, nv_s, max_difference = checkBalance(rolesToAssign, playerCount)
    return [rolesToAssign, str(v_s), str(nv_s), str(max_difference)]


def GetStrenght(role, rolesToAssign, playerCount):
    if role == "Contadino":
        return 1
    elif role == "Ubriaco":
        return 3
    elif role == "Prostituta":
        return 6
    elif role == "Veggente":
        s = 7
        if "Licantropo" in rolesToAssign:
            s += -1
        if "UomoLupo" in rolesToAssign:
            s += -2
        return s
    elif role == "Traditore":
        return 0
    elif role == "Angelo Custode":
        s = 7
        if "Piromane" in rolesToAssign:
            s += 1
        return s
    elif role == "Investigatore":
        return 6
    elif role == "Lupo":
        return 10
    elif role == "Maledetto":
        s = 1
        for Role in rolesToAssign:
            if Role in lupi:
                s += -0.5
        return s
    elif role == "Artigliere":
        return 6
    elif role == "Masochista":
        return playerCount / 2
    elif role == "Folle":
        return 3
    elif role == "Bambino Ribelle":
        return 1
    elif role == "Osservatore":
        s = 1
        if "Veggente" in rolesToAssign:
            s += 4
        if "Folle" in rolesToAssign:
            s += 1
        return s
    elif role == "Apprendista Veggente":
        return 6
    elif role == "Satanista":
        s = 10
        for Role in rolesToAssign:
            if Role not in not_convertible_roles:
                s += 1
        return s
    elif role == "Cacciatore di Satanisti":
        if "Satanista" in rolesToAssign:
            return 7
        else:
            return 1
    elif role == "Massone":
        Masssones = rolesToAssign.count("Massone")
        if Masssones <= 1:
            return 1
        else:
            return Masssones + 3
    elif role == "Sosia":
        return 2
    elif role == "Cupido":
        return 2
    elif role == "Cacciatore Urbano":
        return 6
    elif role == "Serial Killer":
        return 15
    elif role == "Stregone":
        return 2
    elif role == "Lupo Alfa":
        return 12
    elif role == "Cucciolo di Lupo":
        for Role in rolesToAssign:
            if Role in ["Lupo", "Lupo Alfa", "Lupo delle Nevi", "Traditore", "Sosia", "Bambino Ribelle", "Licantropo",
                        "Maledetto"]:
                return 12
        return 10
    elif role == "Fabbro":
        return 5
    elif role == "Goffo":
        return -1
    elif role == "Sindaco":
        return 4
    elif role == "Principe":
        return 3
    elif role == "UomoLupo":
        return 1
    elif role == "Augure":
        return 5
    elif role == "Pacifista":
        return 3
    elif role == "Vecchio Saggio":
        return 3
    elif role == "Oracolo":
        return 4
    elif role == "Morfeo":
        return 3
    elif role == "Licantropo":
        return 10
    elif role == "Ladro":
        return 0
    elif role == "Guastafeste":
        return 5
    elif role == "Chimico":
        return 0
    elif role == "Lupo delle Nevi":
        return 15
    elif role == "Becchino":
        return 8
    elif role == "Piromane":
        return 8
    else:
        return "Assicurati di aver scritto correttamente il ruolo."





# def check_doppioni(rolesToAssign):
#     doppioni = False
#     for role in rolesToAssign:
#         if role in lupi[1:] and rolesToAssign.count(role) > 1:
#             doppioni = True
#     return str(doppioni)


def checkBalance(rolesToAssign, playerCount):
    if not playerCount:
        playerCount = len(rolesToAssign)
    v_n = 0
    v_s = 0
    nv_n = 0
    nv_s = 0
    killers = False
    for role in rolesToAssign:
        if role not in vs["village"]:
            nv_n += 1
            nv_s += GetStrenght(role, rolesToAssign, playerCount)
            if role not in ["Masochista", "Ladro", "Stregone"]:
                killers = True
        else:
            v_n += 1
            v_s += GetStrenght(role, rolesToAssign, playerCount)
    max_difference = (playerCount / 4) + 1
    if nv_n >= v_n or abs(v_s - nv_s) > max_difference or v_n == 0 or nv_n == 0 or not killers:
        return False, None, None, None, None, None
    return True, v_n, v_s, nv_n, nv_s, max_difference


def set_players(update, context):
    names = update.message.text.split("\n")[1:]
    players = context.user_data["current"]
    if len(names) != len(players):
        update.message.reply_text(f"Hai inviato troppi/troppi pochi nomi. "
                                  f"I player del game corrente sono {len(players)}.")
    else:
        context.user_data["current_dict"] = {}
        message = zip(players, names)
        text = ""
        for role, name in message:
            text += f"*{role} | {name}*\n"
            context.user_data["current_dict"][f"{name}"] = {"role": role,
                                                            "about": "",
                                                            "alive": True}
        update.message.reply_markdown(text)


# def set_about(update, context):
#     # set role (and player) description
#     pass


dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("check", check))
dispatcher.add_handler(CommandHandler("random", random))
dispatcher.add_handler(CommandHandler("randomint", randomint))
dispatcher.add_handler(CommandHandler("becchino", becchino))
dispatcher.add_handler(CommandHandler("priority", priority))
dispatcher.add_handler(CommandHandler("link", useful_links))
dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler("quiz", quiz)],
    states={
        ASK_ROLE: [CallbackQueryHandler(ask_role, pattern="get")],
        GET_ANSWER: [MessageHandler(Filters.regex('^\w'), checkAnswer),
                     CallbackQueryHandler(ask_role, pattern="skip"),
                     CommandHandler("skip", ask_role)]
    },
    fallbacks=[CallbackQueryHandler(end, pattern="exit")]
))
# Per /stats
dispatcher.add_handler(ConversationHandler(
    entry_points=[CommandHandler("stats", stats)],
    states={
        GET: [CallbackQueryHandler(get_stats, pattern="[pc]")]
    },
    fallbacks=[CallbackQueryHandler(end, pattern="fb")]
))
# #Per /players
# dispatcher.add_handler(ConversationHandler(
#     entry_points=[CommandHandler("players", players)],
#     states={
#         ASSIGN: [MessageHandler(Filters.regex('^\w'), role_assign)],
#         GAME: [CallbackQueryHandler]
#     },
#     fallbacks=[CallbackQueryHandler(end, pattern="fb")]
# ))
dispatcher.add_handler(MessageHandler(Filters.regex(r'^\d'), generate))
dispatcher.add_handler(MessageHandler(Filters.regex(r'^\w+\n'), custom_game))
dispatcher.add_handler(MessageHandler(Filters.regex(r'^\$'), set_players))
# dispatcher.add_handler(MessageHandler(Filters.regex(r'^\w+,'), set_about))
updater.start_polling()


