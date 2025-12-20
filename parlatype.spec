Name:           parlatype
Version:        2.0.0
Release:        7%{?dist}
Summary:        Speech-to-Text Virtual Keyboard (Italian Edition)

BuildArch:      noarch
%define debug_package %{nil}

License:        MIT
URL:            https://github.com/Enne2/keyTalk
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  python3-devel
BuildRequires:  python3-pip

Requires:       python3
Requires:       python3-devel
Requires:       gcc
Requires:       portaudio-devel
Requires:       gtk4
Requires:       libadwaita
Requires:       unzip
Requires:       wget

%description
ParlaType is a Python application that uses offline speech recognition (Vosk)
to transcribe speech and automatically type it as if it were a physical keyboard.
This version is specifically tuned for the Italian language.

%prep
%setup -q

%build
# No compilation needed for noarch source-based RPM
# Just verify syntax
python3 -m py_compile main.py

%install
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/%{name}
mkdir -p %{buildroot}/usr/share/%{name}/prompts
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps

# Copy source files
cp main.py %{buildroot}/usr/share/%{name}/
cp -r parlatype %{buildroot}/usr/share/%{name}/
cp requirements.txt %{buildroot}/usr/share/%{name}/
cp -r prompts/* %{buildroot}/usr/share/%{name}/prompts/

# Install launcher script
install -m 755 parlatype.sh %{buildroot}/usr/bin/parlatype
install -m 755 parlatype-setup %{buildroot}/usr/bin/

# Install desktop file and icon
sed -i 's|Exec=.*|Exec=/usr/bin/parlatype|' parlatype.desktop
sed -i 's|Icon=.*|Icon=parlatype|' parlatype.desktop
cp parlatype.desktop %{buildroot}/usr/share/applications/
cp parlatype.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/

%post
echo "----------------------------------------------------------------------"
echo "ParlaType installed successfully."
echo "Creating virtual environment and installing dependencies..."
APP_DIR="/usr/share/parlatype"
VENV_DIR="$APP_DIR/venv"

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --no-compile
pip install -r "$APP_DIR/requirements.txt" --no-compile

echo "Downloading the Italian speech model (this may take a while)..."
/usr/bin/parlatype-setup || echo "Model download failed. You can try again manually with: sudo parlatype-setup"
echo "----------------------------------------------------------------------"

%files
/usr/bin/parlatype
/usr/bin/parlatype-setup
/usr/share/%{name}/
/usr/share/applications/parlatype.desktop
/usr/share/icons/hicolor/scalable/apps/parlatype.svg

%changelog
* Sat Dec 20 2025 Matteo Benedetto <matteo@enne2.net> - 2.0.0-7
- Modularize codebase into parlatype package
- Update README and ARCHITECTURE documentation

* Sat Dec 20 2025 Matteo Benedetto <matteo@enne2.net> - 2.0.0-6
- Switch to noarch source-based RPM with venv creation in %post
