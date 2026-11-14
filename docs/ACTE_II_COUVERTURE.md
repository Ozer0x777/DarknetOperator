# Acte II - couverture livrée et limites (0.5.0)

Dix missions et six contrats facultatifs sont intégrés aux contrats, à l’API et
au bureau. Leur qualification joue les commandes, les observations, les choix
et les reprises depuis la fin de l’acte I. Les outils sont exclusivement simulés
sur des machines fictives ; aucun binaire offensif n’est exécuté sur l’ordinateur.

## Ce qui est couvert

- **Inventaire Linux** : id, groups, uname, ip addr/route, ss, ps, sudo -l,
  dpkg-query/dpkg et rpm sur les paquets déclarés, pkexec --version, systemctl,
  stat, getcap et recherche des fichiers SUID. Les paramètres admis sont ceux des
  commandes concernées ; la couverture des options reste finie.
- **Inventaire Windows** : whoami /all, /user, /groups, /priv ; systeminfo, ver,
  route print, netstat, tasklist, sc query, icacls et net. Dans PowerShell :
  Get-CimInstance Win32_OperatingSystem, Get-HotFix et Get-Acl, en plus des
  commandes de fichiers, services et réseau déjà présentes.
- **Données par machine** : système, version, paquets, correctifs, droits, services,
  processus, routes et logiciels présents. Les commandes d’un même scénario
  s’appuient sur ces données communes. Une console Linux distante ne dispose pas
  automatiquement d’Impacket ou de Hashcat.
- **Scripts d’inventaire** : artefacts virtuels LinPEAS et WinPEAS à transférer.
  Ils agrègent les données du modèle sans garantir une exploitation.
- **Polkit** : compilation/interprétation de l’artefact pédagogique fourni,
  conditions de l’image, fichier SUID, image vulnérable et correctif rétroporté.
  Le modèle refuse la même tentative sur l’image corrigée. Le code C et le
  compilateur du jeu ne sont pas un compilateur général ni un exploit réel.
- **SSH -N -L** : port local redirigé vers un service interne depuis le relais,
  authentification, collision de port, console occupée, arrêt/fermeture et reprise.
  L’accès direct à l’adresse interne reste filtré ; le tunnel ne crée pas une
  route globale. La redirection livrée transporte les requêtes HTTP du modèle.
- **LDAP** : ldapsearch, authentification simple avec invite ou secret fourni,
  base, portée base/one/sub, filtres &, |, !, égalité, présence, jokers et
  caractères échappés ; choix des attributs, résultats vides et erreurs.
- **SharpHound** : exécutable virtuel à transférer sur Windows, options de collecte
  et de destination, collecte d’objets et de groupes du domaine puis archive.
  Les droits non observés ne sont pas inventés dans le graphe.
- **BloodHound dans le bureau** : récupération de la collecte, import moteur
  vérifié, objets, relations et recherche. Une collecte altérée ne remplace pas
  le graphe. Cette interface couvre le parcours du jeu, pas toutes les fonctions
  de BloodHound CE ni une reproduction certifiée de son interface.
- **GetUserSPNs / Hashcat 13100** : consultation des SPN, authentification au domaine,
  demande de tickets fictifs RC4-HMAC, export, vérification cryptographique des
  candidats et potfile. Les comptes désactivés sont exclus. Le mode 1000 reste
  disponible pour les empreintes NTLM.

## Limites à conserver visibles

La syntaxe utilisée dans les dossiers est authentique ; **cela ne signifie pas
que toutes les options de chaque programme ou tous les shells sont reproduits**.
Les sorties couvrent les objets et informations présents dans le modèle. Une
option non développée est une limite du simulateur ; elle ne doit pas être
présentée comme une propriété du logiciel réel.

Les collectes ZIP sont des conteneurs virtuels avec des membres JSON. Leur import
est vérifié dans le jeu ; leur compatibilité avec une installation externe de
BloodHound CE n’est pas certifiée. Les méthodes de collecte supplémentaires et
les API complètes de BloodHound restent à étendre. Les cmdlets AD/RSAT, les profils
SASL/TLS LDAP, tous les types Kerberos, les tunnels SOCKS/SSH -D/-J et Ligolo-ng
ne sont pas livrés dans cette version.

Les tickets utilisent un format RC4-HMAC et une vérification HMAC/RC4 sur un corps
fictif ; ils ne donnent aucun accès à un domaine réel. Hashcat 13100 est résolu
immédiatement dans le modèle ; aucun débit GPU ni durée réelle n’est revendiqué.
Les modes AES ne sont pas couverts. Aucun test comparatif contre les binaires
réels des outils ni aucune validation graphique native n’est revendiqué.

Depuis la 0.5.1, les nouvelles carrières utilisent un acte I allégé et une
migration dédiée préserve les dossiers anciens déjà lancés ou terminés.
Les techniques avancées sont proposées dans l’acte II ; voir
[la progression actuelle](ACTE_I_ACTUEL.md).

## Validation reproductible

- `backend/.venv/bin/python -m pytest -q backend/tests`
- `backend/.venv/bin/python backend/act2_validation.py`
- `python3 scripts/check_ui.py`
- `python3 scripts/preview_ui.py`

Les parcours de référence couvrent les dix dossiers, les six secondaires, les
deux décisions du garant, les deux finales, les rechargements et l’équilibre du
portefeuille. Les tests négatifs couvrent correctifs, contexte, logiciels absents,
authentification, filtrage LDAP, tunnel et archives falsifiées. Ils ne remplacent
pas un essai humain de compréhension et de rythme.

## Sources de syntaxe

- OpenSSH : https://man.openbsd.org/ssh
- OpenLDAP : https://www.openldap.org/doc/admin26/quickstart.html
- SharpHound CE : https://bloodhound.specterops.io/collect-data/ce-collection/sharphound-flags
- Impacket GetUserSPNs : https://github.com/fortra/impacket/blob/master/examples/GetUserSPNs.py
- RC4-HMAC : https://www.rfc-editor.org/rfc/rfc4757
- Windows whoami : https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/whoami

Références des images Windows anciennes :
- https://support.microsoft.com/en-gb/servicing/os/windows-11/2023/10/october-10-2023-kb5031354-os-build-22621-2428
- https://learn.microsoft.com/en-us/windows-server/get-started/windows-server-release-info
