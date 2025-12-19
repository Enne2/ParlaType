# ParlaType - Speech-to-Text Virtual Keyboard

**Author:** Matteo Benedetto ([Enne2](https://github.com/Enne2))  
**Website:** [enne2.net](http://enne2.net)

ParlaType è un'applicazione Python che utilizza il riconoscimento vocale offline (Vosk) per trascrivere il parlato e digitarlo automaticamente come se fosse una tastiera fisica. 

**Nota Importante**: Questo progetto è specificamente concepito e ottimizzato per la **lingua italiana**. La mappatura dei tasti e il modello vocale incluso sono configurati per gestire correttamente i caratteri accentati e la fonetica italiana.
tar -tzf ~/rpmbuild/SOURCES/parlatype-1.0.0.tar.gz > /dev/null && echo "Tarball OK" || echo "Tarball Corrupt"
## Caratteristiche

- **Riconoscimento Vocale Offline**: Utilizza Vosk, quindi non richiede connessione internet e garantisce la privacy.
- **Ottimizzato per l'Italiano**: Include il modello `vosk-model-it-0.22` e gestisce nativamente caratteri come `à`, `è`, `é`, `ì`, `ò`, `ù`.
- **Tastiera Virtuale**: Simula la pressione dei tasti tramite `evdev` e `uinput`, permettendo di dettare testo in qualsiasi applicazione.
- **Interfaccia Grafica**: GUI minimale basata su GTK 3 con indicatore nella system tray (se supportato).

## Licenza e Modelli

Il codice sorgente di ParlaType è rilasciato sotto licenza MIT.

Il modello vocale incluso (`vosk-model-it-0.22`) è sviluppato da [Alpha Cephei](https://alphacephei.com/vosk/) ed è rilasciato sotto licenza **Apache 2.0**. È quindi possibile ridistribuirlo liberamente insieme a questa applicazione.
Per maggiori informazioni sui modelli Vosk, visitare la [pagina ufficiale dei modelli](https://alphacephei.com/vosk/models).

## Prerequisiti

Il progetto è sviluppato per **Linux**.

### Dipendenze di Sistema

Prima di installare le dipendenze Python, è necessario installare alcune librerie di sistema. Su sistemi basati su Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install python3-dev python3-pip portaudio19-dev libgirepository1.0-dev libcairo2-dev pkg-config libgirepository1.0-dev
```

### Permessi

L'applicazione necessita di accedere a `/dev/uinput` per creare la tastiera virtuale. Puoi eseguire lo script come root (sconsigliato per l'uso quotidiano) o aggiungere il tuo utente al gruppo `input` (o creare una regola udev specifica).

Per aggiungere l'utente al gruppo `input` (potrebbe richiedere il riavvio o il logout):

```bash
sudo usermod -aG input $USER
```

Inoltre, assicurati che i permessi su `/dev/uinput` siano corretti.

## Installazione

1.  Clona il repository o scarica i file.
2.  Crea un virtual environment (opzionale ma consigliato):

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  Installa le dipendenze Python:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Modello Vosk**:
    Il progetto si aspetta di trovare il modello nella cartella `models/vosk-model-it-0.22`.
    Assicurati che la struttura delle cartelle sia:
    ```
    keyTalk/
    ├── main.py
    ├── models/
    │   └── vosk-model-it-0.22/
    │       ├── model.conf
    │       └── ...
    ```
    Se non hai il modello, scaricalo dal [sito ufficiale di Vosk](https://alphacephei.com/vosk/models) ed estrailo nella cartella `models`.

## Installazione Desktop (Opzionale)

Per integrare ParlaType nel menu delle applicazioni del tuo sistema desktop (GNOME, KDE, ecc.), puoi utilizzare lo script di installazione fornito:

```bash
./install.sh
```

Questo script:
1. Creerà il virtual environment e installerà le dipendenze (se non presenti).
2. Genererà un file `.desktop` con i percorsi corretti.
3. Installerà l'icona e il collegamento nel menu applicazioni.

## Utilizzo

### Da Terminale
Attiva il virtual environment (se creato) ed esegui lo script:

```bash
source .venv/bin/activate
python main.py
```

**Nota**: Se non hai configurato i permessi per il tuo utente, potresti dover usare `sudo`:

```bash
sudo .venv/bin/python main.py
```

Una volta avviato:
1.  L'applicazione inizierà ad ascoltare dal microfono predefinito.
2.  Posiziona il cursore dove vuoi scrivere (es. un editor di testo).
3.  Parla: il testo riconosciuto verrà digitato automaticamente.

## Struttura del Progetto

- `main.py`: Codice principale dell'applicazione (GUI, Thread di trascrizione, Gestione tastiera).
- `requirements.txt`: Elenco delle dipendenze Python.
- `models/`: Cartella contenente i modelli Vosk.

## Risoluzione Problemi

- **Errore `Permission denied` su `/dev/uinput`**: Esegui con `sudo` o configura correttamente i permessi del gruppo `input`.
- **Errore PyAudio**: Assicurati di aver installato `portaudio19-dev`.
- **Caratteri sbagliati**: La mappatura è configurata per un layout di tastiera italiano. Se usi un layout diverso, potresti dover modificare `CHAR_MAP` in `main.py`.
