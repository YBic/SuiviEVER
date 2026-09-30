/**
 * enq_dropdown.js — menu de sélection d'un enquêteur sur un emplacement de vacation.
 *
 * Partagé par l'écran Affectation et l'écran Vacations Zone : les specs §7.3
 * prévoient l'affectation depuis les deux (règle 05 de l'écran principal :
 * « Lors du clic sur une ligne (vacation), la fonctionnalité affectation est
 * activée »). Extrait d'affectation.js pour éviter d'en maintenir deux copies.
 *
 * Le menu est attaché au <body> en position fixed : sinon les conteneurs de
 * tableau en overflow:auto le tronquent.
 */
window.EverEnqDropdown = (function () {

  // Échappement local : escHtml est défini dans la portée privée de chaque
  // écran (affectation.js, vacations_zone.js…), donc invisible ici. Un module
  // partagé ne doit pas dépendre d'une fonction que ses appelants définissent
  // chacun de leur côté.
  function echapper(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /**
   * Remplace le contenu de $td par le menu de sélection.
   *
   * options :
   *   idVacation  identifiant de l'emplacement (ID_Vacation_Enqueteur en aéroport,
   *               ID_Vacation_Zone en zone) — les deux espaces d'identifiants sont
   *               distincts, d'où le paramètre type
   *   idPersonne  occupant actuel, ou null
   *   type        'ZONE' ou 'AEROPORT'
   *   onSaveStart / onSaveEnd  hooks facultatifs (l'écran Affectation s'en sert
   *               pour suspendre son rechargement automatique pendant la sauvegarde)
   *   onSaved     appelé après une sauvegarde réussie
   */
  function build($td, options) {
    const idVacation = options.idVacation;
    const idPersonne = options.idPersonne || null;
    const type       = options.type || 'AEROPORT';

    $td.html(`
      <div class="ever-enq-wrap">
        <div class="input-group input-group-sm">
          <input type="text" class="form-control ever-enq-input" readonly
                 placeholder="Chargement…" style="font-size:12px;min-width:130px">
          <span class="input-group-text ever-enq-caret" style="cursor:pointer">
            <i class="bi bi-caret-down-fill"></i>
          </span>
        </div>
      </div>`);

    const $wrap  = $td.find('.ever-enq-wrap');
    const $input = $td.find('.ever-enq-input');

    const $menu = $('<div class="ever-enq-dropdown"></div>')
      .append('<div class="dropdown-item small py-1" data-id="">— Non affecté —</div>')
      .appendTo('body');

    $.get('/api/affectation/enqueteurs-pour-vacation/', { id_vacation: idVacation, type: type })
    .done(function (resp) {
      if (!resp || resp.status !== 'ok') {
        $td.html('<span class="text-danger small">Erreur chargement</span>');
        $menu.remove();
        return;
      }
      // Zones : les specs (§7.3, règles d'affectation) demandent que les
      // enquêteurs déjà pris à cette date n'apparaissent pas dans le menu.
      // ft_EVER_Liste_Enqueteur_Pour_Affectation_Zone les renvoie quand même,
      // signalés par Affecte_Vacation — on filtre donc ici, en conservant
      // l'occupant actuel du créneau, sans quoi le menu ne pourrait pas
      // afficher la valeur en cours. Côté aéroport la convention historique
      // est maintenue : ils restent proposés, marqués d'une étoile.
      const candidats = type === 'ZONE'
        ? resp.data.filter(e => !e.Affecte_Vacation || e.Id_Personne === idPersonne)
        : resp.data;

      // Tri par nom : le libellé est « Matricule - NOM Prénom », on trie donc
      // sur ce qui suit le premier « - » et non sur le matricule.
      const nomDe = e => { const l = e.Libelle_Enqueteur || ''; const i = l.indexOf(' - '); return i >= 0 ? l.slice(i + 3) : l; };
      candidats.sort((a, b) => nomDe(a).localeCompare(nomDe(b), 'fr', { sensitivity: 'base' }));

      candidats.forEach(function (item) {
        const star = item.Affecte_Vacation
          ? ' <small class="text-warning" title="Déjà affecté à cet horaire">★</small>'
          : '';
        $menu.append(
          `<div class="dropdown-item small py-1" data-id="${item.Id_Personne}">${echapper(item.Libelle_Enqueteur)}${star}</div>`
        );
      });
      const current = idPersonne ? candidats.find(e => e.Id_Personne === idPersonne) : null;
      $input.val(current ? current.Libelle_Enqueteur : '').attr('placeholder', 'Non affecté');
      $td.data('sel-id', idPersonne || null);
    })
    .fail(function () {
      $td.html('<span class="text-danger small">Erreur réseau</span>');
      $menu.remove();
    });

    // Ouverture / fermeture : le menu est positionné sous le groupe input
    $wrap.find('.input-group').on('click', function (e) {
      e.stopPropagation();
      $('.ever-enq-dropdown').not($menu).hide();
      const rect = this.getBoundingClientRect();
      $menu.css({
        top:      rect.bottom + 2,
        left:     rect.left,
        minWidth: rect.width,
        display:  $menu.is(':visible') ? 'none' : 'block',
      });
    });

    $menu.on('click', '.dropdown-item', function (e) {
      e.stopPropagation();
      const newId   = $(this).data('id') || null;
      const newText = $(this).text().replace('★', '').trim();
      $menu.hide();
      if ($td.data('sel-id') == newId) return;
      enregistrer($td, idVacation, newId, newText, type, options);
    });
  }

  function enregistrer($td, idVacation, idPersonne, texte, type, options) {
    if (options.onSaveStart) options.onSaveStart();
    $('body').css('cursor', 'wait');

    const realId = idPersonne ? parseInt(idPersonne) : null;

    ajaxPost('/api/affectation/set/', { id_vacation: idVacation, id_personne: realId, type: type })
    .done(function (resp) {
      if (resp.status !== 'ok') {
        alert('Erreur affectation : ' + (resp.message || ''));
      } else {
        $td.find('.ever-enq-input').val(texte);
        $td.data('sel-id', realId);
        if (options.onSaved) options.onSaved(realId, texte);
      }
    })
    .fail(function () {
      alert('Erreur réseau lors de l\'affectation.');
    })
    .always(function () {
      $('body').css('cursor', 'default');
      if (options.onSaveEnd) options.onSaveEnd();
    });
  }

  // Fermeture des menus au clic ailleurs dans la page
  $(document).on('click', function () {
    $('.ever-enq-dropdown').hide();
  });

  return { build: build };

})();
