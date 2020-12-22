# Nemanja Galbinovic
# December 2020
# CRUD Python Flask App

from flask import Flask, render_template, url_for, request, redirect, session, Response
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash

import mariadb
import ast
import io
import csv

##################################################  KONEKCIJA BAZE    ####################
#paznja na port za mariaDB
konekcija = mariadb.connect(
    user="root",
    password="",
    host="localhost",
    port=3307,
    database="evidencija_studenata"
)
kursor = konekcija.cursor(dictionary=True)
###########################################################################################

app = Flask(__name__)

##################################################  MAIL    ###############################
# Username i password moraju biti legit , kao i mail za korisnika kako bi mu stigla poruka ,
# na gmail mora da se prihvati logovanje preko nepoznatih app
mail = Mail(app)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
#Podaci sa kog maila saljemo poruku
app.config["MAIL_USERNAME"] = "YourEmail"
app.config["MAIL_PASSWORD"] = "YourPassword"
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
mail = Mail(app)


def send_email(ime, prezime, email, lozinka):
    msg = Message(
        subject="Korisnički nalog",
        sender="ATVSS Evidencija studenata",
        recipients=[email],
    )
    msg.html = render_template(
        "email.html", ime=ime, prezime=prezime, lozinka=lozinka)
    mail.send(msg)
    return "Sent"

###########################################################################################

#Sesija
app.secret_key = "tajni_kljuc_aplikacije"

#Funkcija za proveru logovanja
def ulogovan():
    if "ulogovani_korisnik" in session:
        return True
    else:
        return False

#Funkcija ulogovanog korisnika za datom rolom , u ostalim rutama proveravamo za profesora radi restrikcija
def rola():
    if ulogovan():
        return ast.literal_eval(session["ulogovani_korisnik"]).pop("rola")


##################################################  LOGIN/LOGOUT    ################################
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    elif request.method == 'POST':
        forma = request.form
        upit = "SELECT * FROM korisnici WHERE email=%s"
        vrednost = (forma["email"],)
        kursor.execute(upit, vrednost)
        korisnik = kursor.fetchone()
        if check_password_hash(korisnik["lozinka"], forma["lozinka"]):
            # upisivanje korisnika u sesiju
            session["ulogovani_korisnik"] = str(korisnik)
            return redirect(url_for("studenti"))
        else:
            return render_template("login.html")


@app.route("/logout", methods=['GET'])
def logout():
    session.pop("ulogovani_korisnik", None)
    return redirect(url_for("login"))
####################################################################################################

##################################################  STUDENTI    ####################################


@app.route("/studenti", methods=['GET'])
def studenti():
    if ulogovan():
        upit = "SELECT * FROM studenti"
        kursor.execute(upit)
        studenti = kursor.fetchall()
        return render_template("studenti.html", studenti=studenti)
    else:
        return redirect(url_for('login'))


@app.route("/student/<id>", methods=['GET', 'POST'])
def student(id):
    if ulogovan():
        upit = "SELECT * FROM studenti WHERE id=%s"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        student = kursor.fetchone()

        upit = "SELECT * FROM predmeti"
        kursor.execute(upit)
        predmeti = kursor.fetchall()
        #Kako bi ocena_izmena/brisanje radila pre FROM treba dodati ocene.id inace nece raditi , isto uraditi za rute ocena 
        upit = "SELECT predmeti.sifra, predmeti.naziv, predmeti.godina_studija,predmeti.obavezni_izborni,predmeti.espb,ocene.ocena,ocene.id FROM ocene JOIN predmeti ON ocene.predmet_id=predmeti.id WHERE student_id=%s"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        ocene = kursor.fetchall()
        return render_template("student.html", student=student, predmeti=predmeti, ocene=ocene)
    else:
        return redirect(url_for('login'))


@app.route("/student_novi", methods=['GET', 'POST'])
def student_novi():
    if rola() == "Profesor":
        return redirect(url_for("studenti"))

    if ulogovan():
        if request.method == 'GET':
            return render_template("student_novi.html")
        elif request.method == 'POST':
            forma = request.form
            vrednosti = (
                forma["indeks"],
                forma["ime"],
                forma["roditelj"],
                forma["prezime"],
                forma["mail"],
                forma["tel"],
                forma["godina"],
                forma["datum"],
                forma["jmbg"],
                "0",
                "0",
            )
            upit = """ INSERT INTO studenti(broj_indeksa,ime,ime_roditelja,prezime,email,broj_telefona,godina_studija,datum_rodjenja,jmbg,espb,prosek_ocena) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """
            kursor.execute(upit, vrednosti)
            konekcija.commit()
            return redirect(url_for("studenti"))
    else:
        return redirect(url_for('login'))


@app.route("/student_izmena/<id>", methods=['GET', 'POST'])
def student_izmena(id):
    if rola() == "Profesor":
        return redirect(url_for("studenti"))
    if ulogovan():
        if request.method == 'GET':
            upit = "SELECT * FROM studenti WHERE id=%s"
            vrednost = (id,)
            kursor.execute(upit, vrednost)
            student = kursor.fetchone()
            return render_template("student_izmena.html", student=student)
        elif request.method == 'POST':
            forma = request.form
            vrednosti = (
                forma["indeks"],
                forma["ime"],
                forma["roditelj"],
                forma["prezime"],
                forma["mail"],
                forma["tel"],
                forma["godina"],
                forma["datum"],
                forma["jmbg"],
                id,
            )
            upit = """UPDATE studenti SET 
            broj_indeksa=%s, 
            ime = %s,
            ime_roditelja = %s,
            prezime=%s, 
            email=%s, 
            broj_telefona=%s,
            godina_studija = %s,
            datum_rodjenja = %s,
            jmbg = %s
            WHERE id=%s 
            """
            kursor.execute(upit, vrednosti)
            konekcija.commit()
            return redirect(url_for("studenti"))
    else:
        return redirect(url_for('login'))


@app.route("/student_brisanje/<id>", methods=['GET', 'POST'])
def student_brisanje(id):
    if rola() == "Profesor":
        return redirect(url_for("studenti"))
    if ulogovan():
        upit = """ DELETE FROM studenti WHERE id=%s"""
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        konekcija.commit()
        return redirect(url_for("studenti"))
    else:
        return redirect(url_for('login'))
####################################################################################################

##################################################  PREDMETI    ####################################


@app.route("/predmeti", methods=['GET'])
def predmeti():
    if rola() == "Profesor":
        return redirect(url_for("studenti"))
    if ulogovan():
        upit = "SELECT * FROM predmeti"
        kursor.execute(upit)
        predmeti = kursor.fetchall()
        return render_template("predmeti.html", predmeti=predmeti)
    else:
        return redirect(url_for('login'))


@app.route("/predmet_novi", methods=['GET', 'POST'])
def predmet_novi():
    if rola() == "Profesor":
        return redirect(url_for("predmeti"))
    if ulogovan():
        if request.method == 'GET':
            return render_template("predmet_novi.html")
        elif request.method == 'POST':
            forma = request.form
            vrednosti = (
                forma["sifra"],
                forma["naziv"],
                forma["studija"],
                forma["espb"],
                forma["oi"],
            )
            upit = """ INSERT INTO predmeti(sifra,naziv,godina_studija,espb,obavezni_izborni) VALUES (%s, %s, %s, %s, %s) """
            kursor.execute(upit, vrednosti)
            konekcija.commit()
            return redirect(url_for("predmeti"))
    else:
        return redirect(url_for('login'))


@app.route("/predmet_izmena/<id>", methods=['GET', 'POST'])
def predmet_izmena(id):
    if rola() == "Profesor":
        return redirect(url_for("predmeti"))
    if ulogovan():
        if request.method == 'GET':
            upit = "SELECT * FROM predmeti WHERE id=%s"
            vrednost = (id,)
            kursor.execute(upit, vrednost)
            predmet = kursor.fetchone()
            return render_template("predmet_izmena.html", predmet=predmet)
        elif request.method == 'POST':
            forma = request.form
            vrednosti = (
                forma["sifra"],
                forma["naziv"],
                forma["studija"],
                forma["espb"],
                forma["oi"],
                id,
            )
            upit = """UPDATE predmeti SET 
            sifra=%s, 
            naziv=%s, 
            godina_studija=%s, 
            espb=%s,
            obavezni_izborni=%s 
            WHERE id=%s 
            """
            kursor.execute(upit, vrednosti)
            konekcija.commit()
            return redirect(url_for("predmeti"))
    else:
        return redirect(url_for('login'))


@app.route("/predmet_brisanje/<id>", methods=['GET', 'POST'])
def predmet_brisanje(id):
    if rola() == "Profesor":
        return redirect(url_for("predmeti"))
    if ulogovan():
        upit = """
            DELETE FROM predmeti WHERE id=%s
        """
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        konekcija.commit()
        return redirect(url_for("predmeti"))
    else:
        return redirect(url_for('login'))
####################################################################################################

##################################################  KORISNICI    ###################################


@app.route("/korisnici", methods=['GET'])
def korisnici():
    if rola() == "Profesor":
        return redirect(url_for("studenti"))
    if ulogovan():
        upit = "SELECT * FROM korisnici"
        kursor.execute(upit)
        korisnici = kursor.fetchall()
        return render_template("korisnici.html", korisnici=korisnici)
    else:
        return redirect(url_for('login'))


@app.route("/korisnik_novi", methods=['GET', 'POST'])
def korisnik_novi():
    if rola() == "Profesor":
        return redirect(url_for("korisnici"))
    if ulogovan():
        if request.method == 'GET':
            return render_template("korisnik_novi.html")
        elif request.method == 'POST':
            forma = request.form
            #Hesovanje lozinke(Ako dodajemo direktno u bazi preko phpmyadmin nece raditi login jer sifra nece biti hesovana)
            hesovana_lozinka = generate_password_hash(forma["lozinka"])
            vrednosti = (
                forma["ime"],
                forma["prezime"],
                forma["email"],
                hesovana_lozinka,
                forma["rola"],
            )
            upit = """ INSERT INTO korisnici(ime,prezime,email,lozinka,rola) VALUES (%s, %s, %s, %s, %s) """
            kursor.execute(upit, vrednosti)
            konekcija.commit()
            send_email(forma["ime"], forma["prezime"],
                       forma["email"], forma["lozinka"])
            return redirect(url_for("korisnici"))
    else:
        return redirect(url_for('login'))


@app.route("/korisnik_izmena/<id>", methods=['GET', 'POST'])
def korisnik_izmena(id):
    if rola() == "Profesor":
        return redirect(url_for("korisnici"))
    if ulogovan():
        if request.method == 'GET':
            upit = "SELECT * FROM korisnici WHERE id=%s"
            vrednost = (id,)
            kursor.execute(upit, vrednost)
            korisnik = kursor.fetchone()
            return render_template("korisnik_izmena.html", korisnik=korisnik)
        elif request.method == 'POST':
            forma = request.form
            hashovana_lozinka = generate_password_hash(forma["lozinka"])
            vrednosti = (
                forma["ime"],
                forma["prezime"],
                forma["email"],
                hashovana_lozinka,
                id,
            )
            upit = """UPDATE korisnici SET 
            ime=%s, 
            prezime=%s, 
            email=%s, 
            lozinka=%s 
            WHERE id=%s 
            """
            kursor.execute(upit, vrednosti)
            konekcija.commit()
            return redirect(url_for("korisnici"))
    else:
        return redirect(url_for('login'))


@app.route("/korisnik_brisanje/<id>", methods=['GET', 'POST'])
def korisnik_brisanje(id):
    if rola() == "Profesor":
        return redirect(url_for("korisnici"))
    if ulogovan():
        upit = """
            DELETE FROM korisnici WHERE id=%s
        """
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        konekcija.commit()
        return redirect(url_for("korisnici"))
    else:
        return redirect(url_for('login'))
####################################################################################################

##################################################  OCENA    #######################################


@app.route("/ocena_nova/<id>", methods=["POST"])
def ocena_nova(id):
    if ulogovan():
        # Dodavanje ocene u tabelu ocene
        upit = """
            INSERT INTO ocene(student_id, predmet_id, ocena, datum)
            VALUES(%s, %s, %s, %s)
        """
        forma = request.form
        vrednosti = (id, forma['predmet_id'], forma['ocena'], forma['datum'])
        kursor.execute(upit, vrednosti)
        konekcija.commit()

        # Računanje proseka ocena
        upit = "SELECT AVG(ocena) AS rezultat FROM ocene WHERE student_id=%s"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        prosek_ocena = kursor.fetchone()

        # Računanje ukupno espb
        upit = "SELECT SUM(espb) AS rezultat FROM predmeti WHERE id IN (SELECT predmet_id FROM ocene WHERE student_id=%s)"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        espb = kursor.fetchone()

        # Izmena tabele student
        upit = "UPDATE studenti SET espb=%s, prosek_ocena=%s WHERE id=%s"
        vrednosti = (espb['rezultat'], prosek_ocena['rezultat'], id)
        kursor.execute(upit, vrednosti)
        konekcija.commit()
        return redirect(url_for('student', id=id))
    else:
        return redirect(url_for('login'))


@app.route("/ocena_izmena/<id>/<ocena_id>", methods=['GET', 'POST'])
def ocena_izmena(id, ocena_id):
    if ulogovan():
        if request.method == 'GET':
            upit = "SELECT * FROM studenti WHERE id=%s"
            vrednost = (id,)
            kursor.execute(upit, vrednost)
            student = kursor.fetchone()

            upit = "SELECT * FROM predmeti"
            kursor.execute(upit)
            predmeti = kursor.fetchall()

            upit = "SELECT predmeti.sifra, predmeti.naziv, predmeti.godina_studija,predmeti.obavezni_izborni,predmeti.espb,ocene.ocena,ocene.id FROM ocene JOIN predmeti ON ocene.predmet_id=predmeti.id WHERE student_id=%s"
            vrednost = (id,)
            kursor.execute(upit, vrednost)
            ocene = kursor.fetchall()

            upit = "SELECT * FROM ocene WHERE id=%s"
            vrednost = (ocena_id,)
            kursor.execute(upit, vrednost)
            data_ocena = kursor.fetchone()
            return render_template("ocena_izmena.html", student=student, predmeti=predmeti, ocene=ocene, data_ocena=data_ocena, id=id)
        elif request.method == 'POST':
            forma = request.form

            vrednosti = {
                forma['predmet_id'],
                forma['ocena'],
                forma['datum'],
                id,
            }

            upit = """ UPDATE ocene SET predmet_id = %s, ocena=%s, datum=%s WHERE id=%s """
            kursor.execute(upit, vrednost)

            # Računanje proseka ocena
            upit = "SELECT AVG(ocena) AS rezultat FROM ocene WHERE student_id=%s"
            vrednost = (id,)
            kursor.execute(upit, vrednost)
            prosek_ocena = kursor.fetchone()

            # Računanje ukupno espb
            upit = "SELECT SUM(espb) AS rezultat FROM predmeti WHERE id IN (SELECT predmet_id FROM ocene WHERE student_id=%s)"
            vrednost = (id,)
            kursor.execute(upit, vrednost)
            espb = kursor.fetchone()

            # Izmena tabele student
            upit = "UPDATE studenti SET espb=%s, prosek_ocena=%s WHERE id=%s"
            vrednosti = (espb['rezultat'], prosek_ocena['rezultat'], id)
            kursor.execute(upit, vrednosti)
            konekcija.commit()
            return redirect(url_for('student', id=id))
    else:
        return redirect(url_for('login'))


@app.route("/ocena_brisanje/<id>/<ocena_id>", methods=['GET', 'POST'])
def ocena_brisanje(id, ocena_id):
    if ulogovan():
        upit = """ DELETE FROM ocene WHERE id=%s"""

        vrednost = (ocena_id,)

        kursor.execute(upit, vrednost)

        # Računanje proseka ocena
        upit = "SELECT AVG(ocena) AS rezultat FROM ocene WHERE student_id=%s"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        prosek_ocena = kursor.fetchone()

        # Računanje ukupno espb
        upit = "SELECT SUM(espb) AS rezultat FROM predmeti WHERE id IN (SELECT predmet_id FROM ocene WHERE student_id=%s)"
        vrednost = (id,)
        kursor.execute(upit, vrednost)
        espb = kursor.fetchone()

        # Izmena tabele student
        upit = "UPDATE studenti SET espb=%s, prosek_ocena=%s WHERE id=%s"
        vrednosti = (espb['rezultat'], prosek_ocena['rezultat'], id)
        kursor.execute(upit, vrednosti)
        konekcija.commit()
        return redirect(url_for('student', id=id))
    else:
        return redirect(url_for('login'))
####################################################################################################

##################################################  EXPORT    ######################################


@app.route("/export/<tip>")
def export(tip):
    switch = {
        "studenti": "SELECT * FROM studenti",
        "korisnici": "SELECT * FROM korisnici",
        "predmeti": "SELECT * FROM predmeti",
    }
    upit = switch.get(tip)

    kursor.execute(upit)
    rezultat = kursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)

    for row in rezultat:
        red = []
        for value in row.values():
            red.append(str(value))
        writer.writerow(red)

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=" + tip + ".csv"},
    )
####################################################################################################

#Svaki put kada sacuvamo izmene ono automatski pokrece aplikaciju kako ne bi kontanstno pisali py App.py (dobro koristiti tokom obrade projekta)
app.run(debug=True)
