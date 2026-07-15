# NOTE — Réponse au marché public AUXR_LOGIS réf. 2026-48

> À coller/ré-uploader dans une nouvelle session Claude pour préparer la réponse à cet appel d'offres.

## 1. Le marché
- **Acheteur** : AUXR_LOGIS (bailleur social, Bourgogne-Franche-Comté — secteur Auxerre/Yonne probable).
- **Plateforme** : Ternum BFC — `https://marches.ternum-bfc.fr/entreprise/consultation/691378?orgAcronyme=a0c1`
- **Référence** : 2026-48
- **Échéance** : remise des offres **aujourd'hui, 17h00 max** (dépôt dématérialisé sur la plateforme — prévoir 30–45 min de marge, 17h00:01 = rejet).
- ⚠️ DCE non encore lu (plateforme bloquée à l'accès automatisé). **Première action : télécharger le DCE** (RC, CCTP, CCAP, Acte d'engagement, BPU/DPGF) et me le fournir / en coller le contenu.

## 2. L'entreprise qui répond — ADOMSENIOR
- Activité : **transformation baignoire → douche sécurisée PMR/seniors**, posée **en 1 journée**, en **site occupé**.
- Méthode : on **recouvre les murs de panneaux étanches (PMMA, fournisseur LT Showertec)** — **sans casser, sans carrelage, sans percer** → réponse amiante. Receveur extra-plat, paroi verre, barre de maintien, siège, mitigeur thermostatique.
- Atouts marché public : **équipes certifiées amiante SS4**, **interlocuteur unique**, **suivi numérique (logiciel INTERFAST)**, démarche RSE (gestion déchets), respect du locataire. **Douche utilisable après 36 h** de séchage.
- Preuve sociale : **3 000+ installations**, **~50 poses/mois**, garantie **décennale**.
- Nom commercial : ADOMSENIOR (ex-SENIORADOM). Entité : LYES SANITAIRE / ETS OUHADDAD (Jurançon 64).

## 3. Ce que doit faire la prochaine session Claude
1. Lire le **RC + CCTP** (fournis par l'utilisateur) et en extraire : objet exact, **allotissement** (lots), **critères d'attribution** (prix vs valeur technique), **pièces exigées**, délais d'exécution, heure limite.
2. **Adapter le mémoire technique existant** (voir §5) à CETTE consultation : présentation entreprise, moyens humains/matériels, **méthodologie de pose panneaux + étanchéité (4 barrages)**, planning 1 jour, sécurité amiante SS4, gestion des déchets, respect locataire en site occupé, SAV/garantie.
3. Aider à assembler la **candidature** et l'**offre** (checklist §4).
4. Ne rien inventer sur les montants : le **chiffrage (BPU/DPGF)** reste à faire par l'utilisateur.

## 4. Checklist des pièces (marché public travaux / adaptation PMR)
**Candidature :**
- [ ] DUME **ou** DC1 (lettre de candidature) + DC2 (déclaration du candidat)
- [ ] Attestations fiscales et sociales à jour (URSSAF, impôts)
- [ ] Attestation **assurance décennale** + **RC professionnelle**
- [ ] Extrait **Kbis** (< 3 mois)
- [ ] **Attestation / certification amiante SS4**
- [ ] Références de chantiers similaires (bailleurs sociaux)

**Offre :**
- [ ] **Acte d'engagement** (ATTRI1) complété et signé
- [ ] **BPU / DPGF** chiffré (prix)
- [ ] **Mémoire technique** (adapté à la consultation)
- [ ] Éventuels : planning, fiches produits LT Showertec, attestations de visite

## 5. Ressources réutilisables (déjà fournies par l'utilisateur)
Dans les uploads de session précédente (`/root/.claude/uploads/9aefad33-.../`) :
- `4_MEMOIRE_TECHNIQUE_FRANCE_LOIRE_VF.docx` et `M_moire_technique_ERILIA_LOT_8.docx` → **bases de mémoire technique** à adapter.
- `Pr_sentation_institutionnelle_2023.pdf` → présentation entreprise.
- `ETAPES_DE_LINSTALLATION.pdf`, `AVANT_APRES.pdf`, catalogue **LT Showertec** → visuels/argumentaire.
- Documents ADOMSENIOR déjà refaits (charte à jour) dans le repo site : `documents/` (PV de réception, notice d'entretien, VISAP) + logo `public/logo-adomsenior.*`.
> ⚠️ Ces fichiers ne sont pas transférés automatiquement d'une session à l'autre : **ré-uploader** le mémoire technique + le DCE dans la nouvelle session.

## 6. Contexte / pourquoi ce marché a failli être manqué
- La **veille** (`ANALYSE-MARCHES`) **n'a pas tourné depuis le 2 juillet** et n'est **pas automatisée** (lancement manuel `lancer.bat`).
- **Ternum BFC n'est pas couverte** par l'outil (comme achatpublic, chargée en JS / bloquée au scraping direct).
- À corriger après le dépôt : automatiser la veille (tâche planifiée quotidienne + alerte mail), brancher les **flux RSS** des plateformes (Ternum BFC, achatpublic, marches-sécurisés) et ajouter une **alerte « échéance < 5 jours »**.

## 7. Codes CPV de référence ADOMSENIOR
45332400 (appareils sanitaires) · 45330000 (plomberie) · 45332000 (évacuation) · 45211310 (salles de bains) · 44411000 (articles sanitaires) · 45454100 (rénovation).
