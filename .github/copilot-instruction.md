# Istruzioni per GitHub Copilot (e altri agenti AI)

Questo documento fornisce contesto e linee guida specifiche per lavorare su questo progetto "ParlaType".

## Panoramica del Progetto
ParlaType è un sistema di dettatura vocale per Linux che inietta l'input direttamente nel sistema operativo come una tastiera virtuale.

## Stack Tecnologico
- **OS**: Linux (Esclusivo). Non compatibile con Windows/macOS a causa di `evdev`.
- **Audio**: `pyaudio` per la cattura, `vosk` per il riconoscimento vocale offline.
- **Input Injection**: `python-evdev` (interfaccia a `/dev/uinput`).
- **GUI**: GTK 3 tramite `PyGObject` (`gi.repository`).

## Linee Guida per la Generazione di Codice

### 1. Gestione Input (VirtualKeyboard)
- La classe `VirtualKeyboard` usa `evdev.UInput`.
- **Importante**: La mappatura dei tasti (`CHAR_MAP`) è hardcodata per un layout di tastiera **Italiano**.
- Se suggerisci modifiche alla digitazione, ricorda che `evdev` invia scancode fisici, non caratteri Unicode. Per digitare una 'È' maiuscola, bisogna simulare `SHIFT` + `è` (che è `KEY_LEFTBRACE` nel layout IT), oppure usare combinazioni specifiche.
- Ricorda sempre di chiamare `ui.syn()` dopo aver inviato eventi per renderli effettivi.

### 2. Concorrenza e Threading
- L'applicazione usa `threading` per il riconoscimento vocale (`Transcriber`) per non bloccare il main loop GTK.
- **Non** eseguire operazioni bloccanti (come `rec.AcceptWaveform`) nel thread principale della GUI.
- Usa `GLib.idle_add` o simili se devi aggiornare la GUI dal thread del trascrittore.

### 3. Gestione Errori e Permessi
- L'errore più comune è `PermissionError` su `/dev/uinput`.
- Quando scrivi codice di inizializzazione o test, gestisci sempre il caso in cui `UInput` fallisce (es. `self.available = False`), permettendo all'app di avviarsi (magari solo in modalità log) senza crashare.

### 4. Dipendenze
- Ricorda che `PyGObject` e `pyaudio` richiedono pacchetti di sistema (`libcairo2-dev`, `libgirepository1.0-dev`, `portaudio19-dev`) per essere installati via pip. Includi questi passaggi se spieghi come configurare l'ambiente.

### 5. Percorsi
- Il modello Vosk è caricato usando un percorso relativo a `__file__`. Mantieni questo pattern per portabilità:
  ```python
  os.path.join(os.path.dirname(__file__), "models/...")
  ```

## Comandi Utili per Agenti
- Per eseguire l'app: `python main.py` (spesso richiede `sudo`).
- Per installare deps: `pip install -r requirements.txt`.
