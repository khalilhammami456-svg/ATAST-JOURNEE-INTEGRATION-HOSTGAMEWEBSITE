# Hébergement gratuit : machine virtuelle Oracle Cloud « Always Free »

La plateforme ATAST est un serveur Node avec une base SQLite : elle a besoin d'un **disque qui survit aux redémarrages**. L'offre gratuite d'Oracle Cloud fournit une machine virtuelle toujours allumée avec un vrai disque, sans modifier le code. Le script `setup.sh` installe tout : Node 22, redémarrage automatique, HTTPS gratuit (Caddy), pare-feu, sauvegarde quotidienne.

> Les conditions de l'offre gratuite changent : vérifiez-les sur oracle.com/cloud/free avant de commencer. Une **carte bancaire est demandée pour vérifier l'identité** (aucun débit tant que vous restez sur les ressources « Always Free »). Oracle peut récupérer une machine gratuite restée inactive très longtemps : un site de club utilisé régulièrement n'est pas concerné, mais gardez des sauvegardes hors de la machine.

## 1. Créer la machine (une seule fois, environ 15 minutes)

1. Créer un compte sur oracle.com/cloud/free. **Choisissez bien la région d'origine** (Frankfurt, Marseille…) : elle ne se change plus.
2. Console → **Compute → Instances → Create instance** :
   - **Image** : Ubuntu 24.04 (ou 22.04).
   - **Shape** : choisir une forme marquée « Always Free eligible » : `VM.Standard.A1.Flex` (ARM, 1 OCPU / 6 Go suffisent) ou, si aucune capacité n'est disponible, `VM.Standard.E2.1.Micro`.
   - **Networking** : réseau public, adresse IPv4 publique attribuée.
   - **SSH keys** : *Generate a key pair* et **télécharger la clé privée** (à garder précieusement).
3. Ouvrir les ports web : instance → sous-réseau (*Subnet*) → **Security List** → *Add Ingress Rules* :
   `Source CIDR 0.0.0.0/0`, protocole TCP, port **80**, puis une seconde règle pour le port **443**.

## 2. Installer la plateforme

Depuis votre ordinateur (remplacez l'adresse IP et le chemin de la clé) :

```bash
ssh -i ~/clé-oracle.key ubuntu@ADRESSE_IP
```

Puis, sur la machine :

```bash
git clone https://github.com/khalilhammami456-svg/ATAST-JOURNEE-INTEGRATION-HOSTGAMEWEBSITE.git
cd ATAST-JOURNEE-INTEGRATION-HOSTGAMEWEBSITE
git checkout claude/file-exploration-vtllhw      # ou main une fois la branche fusionnée
sudo bash atast-platform/deploy/oracle/setup.sh
```

Le script affiche l'adresse du site, du type `https://12-34-56-78.sslip.io` (nom gratuit construit à partir de l'IP). Pour utiliser **votre propre nom de domaine**, créez d'abord un enregistrement DNS `A` vers l'IP de la machine, puis :

```bash
sudo DOMAIN=membres.exemple.tn bash atast-platform/deploy/oracle/setup.sh
```

Dépôt privé ? Cloner avec un jeton d'accès personnel GitHub (`https://<jeton>@github.com/...`), ou copier le dossier `atast-platform` avec `scp -r`.

## 3. Créer l'administrateur et commencer

```bash
sudo atast-admin "Bureau ATAST" bureau@atast.tn +21673000000     # le mot de passe est demandé sans s'afficher
```

Ouvrez l'adresse du site, connectez-vous, allez dans **Cotisations** et importez la liste Excel.

## Au quotidien

| Besoin | Commande (sur la machine) |
|---|---|
| Mettre à jour le site | `cd ATAST-…; git pull; sudo bash atast-platform/deploy/oracle/update.sh` (sauvegarde automatique avant) |
| Voir les journaux | `sudo journalctl -u atast -f` |
| Redémarrer | `sudo systemctl restart atast` |
| Sauvegarde immédiate | `sudo atast-backup` |
| Voir l'état | `sudo systemctl status atast caddy` |

**Données** : base `/var/lib/atast/atast.sqlite`, photos `/var/lib/atast/uploads`, sauvegardes quotidiennes à 3 h dans `/var/lib/atast/backups` (30 conservées). Configuration : `/etc/atast/atast.env`.

**Sauvegarde hors de la machine** (recommandé, au moins chaque mois), depuis votre ordinateur :

```bash
scp -i ~/clé-oracle.key -r ubuntu@ADRESSE_IP:/var/lib/atast/backups ./sauvegardes-atast
```

**Restaurer** : `sudo systemctl stop atast`, copier un fichier de sauvegarde sur `/var/lib/atast/atast.sqlite` (supprimer `atast.sqlite-wal` et `-shm`), `sudo chown atast:atast /var/lib/atast/atast.sqlite`, `sudo systemctl start atast`.

## En cas de problème

- **Le site ne s'ouvre pas** : vérifier les règles 80/443 dans la *Security List* d'Oracle ; sur la machine `curl -I http://127.0.0.1:3000/healthz` doit répondre `200`.
- **Erreur de certificat** : le DNS doit pointer vers l'IP de la machine ; `sudo journalctl -u caddy -n 50`.
- **L'application ne démarre pas** : `sudo journalctl -u atast -n 50`.
