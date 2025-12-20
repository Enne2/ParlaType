# ParlaType - Speech-to-Text Virtual Keyboard

**Author:** Matteo Benedetto ([Enne2](https://github.com/Enne2))  
**Website:** [enne2.net](http://enne2.net)

ParlaType è un'applicazione Python che utilizza il riconoscimento vocale offline (Vosk) per trascrivere il parlato e digitarlo automaticamente come se fosse una tastiera fisica. 

**Nota Importante**: Questo progetto è specificamente concepito e ottimizzato per la **lingua italiana**. La mappatura dei tasti e il modello vocale incluso sono configurati per gestire correttamente i caratteri accentati e la fonetica italiana.

## Caratteristiche

- **Riconoscimento Vocale Offline**: Utilizza Vosk, quindi non richiede connessione internet e garantisce la privacy.
- **Ottimizzato per l'Italiano**: Include il supporto per il modello `vosk-model-it-0.22` e gestisce nativamente caratteri come `à`, `è`, `é`, `ì`, `ò`, `ù`.
- **Tastiera Virtuale**: Simula la pressione dei tasti tramite `evdev` e `uinput`, permettendo di dettare testo in qualsiasi applicazione.
- **Interfaccia Moderna**: GUI basata su **GTK 4** e **Libadwaita** per un'integrazione perfetta con gli ambienti desktop moderni (come GNOME).
- **Integrazione LLM**: Supporto opzionale per il post-processing del testo tramite modelli di linguaggio (LLM) per correggere la punteggiatura e la grammatica.

## Installazione

### Pacchetti Pronti (Consigliato)

Puoi scaricare i pacchetti precompilati dalla sezione [Releases](https://git.enne2.net/enne2/parlaType/releases):

- **Fedora/RPM**: `sudo dnf install ./parlatype-2.0.0-6.fc43.noarch.rpm`
- **Debian/Ubuntu/DEB**: `sudo apt install ./parlatype_2.0.0-7_all.deb`

Questi pacchetti installeranno automaticamente tutte le dipendenze e configureranno un ambiente virtuale isolato in `/usr/share/parlatype/venv`.

### Da Sorgente (Sviluppo)

1.  Clona il repository.
2.  Installa le dipendenze di sistema (Fedora):
    ```bash
    sudo dnf install python3-devel portaudio-devel libadwaita-devel gobject-introspection-devel
    ```
3.  Crea un virtual environment e installa le dipendenze Python:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
4.  Esegui lo script di installazione locale:
    ```bash
    ./install.sh
    ```

## Configurazione Modello Vocale

L'applicazione richiede il modello italiano di Vosk. Se installi tramite RPM/DEB o usi lo script di installazione, puoi scaricare il modello automaticamente eseguendo:

```bash
parlatype-setup
```

Oppure scaricalo manualmente da [Vosk Models](https://alphacephei.com/vosk/models) ed estrailo in `models/vosk-model-it-0.22`.

## Permessi

L'applicazione necessita di accedere a `/dev/uinput`. Assicurati che il tuo utente faccia parte del gruppo `input`:

```bash
sudo usermod -aG input $USER
```
*(Potrebbe essere necessario il riavvio)*.

## Licenza

Rilasciato sotto licenza MIT. Il modello vocale Vosk è rilasciato sotto licenza Apache 2.0.
