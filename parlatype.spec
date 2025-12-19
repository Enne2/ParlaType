Name:           parlatype
Version:        2.0.0
Release:        2%{?dist}
Summary:        Speech-to-Text Virtual Keyboard (Italian Edition)

%define debug_package %{nil}

License:        MIT
URL:            https://github.com/Enne2/keyTalk
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  python3-devel
BuildRequires:  python3-pip
BuildRequires:  gcc
# Dependencies for PyInstaller and the app
BuildRequires:  portaudio-devel
BuildRequires:  gtk4-devel
BuildRequires:  libadwaita-devel

Requires:       portaudio
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
# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Compile with PyInstaller using all available cores for the build process
# Note: PyInstaller itself doesn't have a -j flag, but we can run it.
pyinstaller --noconfirm main.spec

%install
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/lib/%{name}
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps

# Copy the compiled files
cp -r dist/main/* %{buildroot}/usr/lib/%{name}/

# Install setup script
install -m 755 parlatype-setup %{buildroot}/usr/bin/

# Create a symlink to the binary
ln -s /usr/lib/%{name}/parlatype %{buildroot}/usr/bin/parlatype

# Install desktop file and icon
sed -i 's|Exec=.*|Exec=/usr/bin/parlatype|' parlatype.desktop
sed -i 's|Icon=.*|Icon=parlatype|' parlatype.desktop
cp parlatype.desktop %{buildroot}/usr/share/applications/
cp parlatype.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/

%post
echo "----------------------------------------------------------------------"
echo "ParlaType installed successfully."
echo "Downloading the Italian speech model (this may take a while)..."
/usr/bin/parlatype-setup || echo "Model download failed. You can try again manually with: sudo parlatype-setup"
echo "----------------------------------------------------------------------"

%files
/usr/bin/parlatype
/usr/bin/parlatype-setup
/usr/lib/%{name}/
/usr/share/applications/parlatype.desktop
/usr/share/icons/hicolor/scalable/apps/parlatype.svg

%changelog
* Fri Dec 19 2025 Matteo Benedetto <matteo@enne2.net> - 1.0.0-1
- Initial RPM release
