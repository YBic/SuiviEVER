/**
 * affectation.js — Affectation des enquêteurs aux vacations
 * UX alignée DGAC : clic sur ligne = expand + dropdown Bootstrap inline,
 * re-clic ou clic hors tableau = fermeture + rechargement.
 */

$(function () {

  let $selectedRow   = null;
  let savedScrollTop = 0;
  let isSavingAffect = false;

  // ── Persistance des filtres ──────────────────────────────────────────────
  const FS = {
    save() {
      sessionStorage.setItem('ever.date',                   $('#filter-date').val());
      sessionStorage.setItem('ever.affectation.type_site',  $('#filter-type-site').val());
      sessionStorage.setItem('ever.affectation.aeroport',   $('#filter-aeroport').val());
      sessionStorage.setItem('ever.affectation.site',       $('#filter-site').val());
      sessionStorage.setItem('ever.affectation.enqueteur',  $('#filter-enqueteur').val());
    },
    restore() {
      const date     = sessionStorage.getItem('ever.date');
      const typeSite = sessionStorage.getItem('ever.affectation.type_site');
      setFilterDate(date);
      if (typeSite) {
        $('#filter-type-site').val(typeSite);
        const isAero = typeSite === 'AEROPORT';
        $('#group-aeroport').toggleClass('d-none', !isAero);
        $('#group-site').toggleClass('d-none', isAero);
      }
    },
  };
  FS.restore();

  // ── Init ────────────────────────────────────────────────────────────────
  loadSitesEtAeroports();
  loadData();
  window.everReloadData = loadData;

  // ── Événements filtres ───────────────────────────────────────────────────
  $('#filter-type-site').on('change', function () {
    const isAero = $(this).val() === 'AEROPORT';
    $('#group-aeroport').toggleClass('d-none', !isAero);
    $('#group-site').toggleClass('d-none', isAero);
    FS.save();
    loadSitesEtAeroports();
    loadData();
  });

  $('#filter-date').on('change', function () {
    FS.save();
    loadSitesEtAeroports();
    loadData();
  });

  $('#filter-aeroport, #filter-site').on('change', function () {
    FS.save();
    loadEnqueteursFiltre();
    loadData();
  });

  $('#filter-enqueteur').on('change', function () {
    FS.save();
    loadData();
  });

  $('#btn-refresh-data').on('click', loadData);
  $('#btn-close-detail').on('click', () => $('#panel-detail-vacation').addClass('d-none'));

  // ── Chargement dropdowns filtres ──────────────────────────────────────────
  function loadSitesEtAeroports() {
    const date   = $('#filter-date').val();
    const isAero = $('#filter-type-site').val() === 'AEROPORT';
    if (isAero) {
      $.get('/api/aeroports/', { date }).done(function (resp) {
        if (resp.status !== 'ok') return;
        const $sel = $('#filter-aeroport');
        const prev = $sel.val() || sessionStorage.getItem('ever.affectation.aeroport');
        $sel.find('option:not(:first)').remove();
        resp.data.forEach(a => $sel.append(
          `<option value="${a.Id_Aeroport}">${a.Code_Aeroport} – ${a.Nom_Aeroport}</option>`
        ));
        if (prev) $sel.val(prev);
        loadEnqueteursFiltre();
      });
    } else {
      $.get('/api/sites/', { date }).done(function (resp) {
        if (resp.status !== 'ok') return;
        const $sel = $('#filter-site');
        const prev = $sel.val() || sessionStorage.getItem('ever.affectation.site');
        $sel.find('option:not(:first)').remove();
        resp.data.forEach(s => $sel.append(
          `<option value="${s.Id_Site}">[${s.Type_Site}] ${s.Nom_Site}</option>`
        ));
        if (prev) $sel.val(prev);
        loadEnqueteursFiltre();
      });
    }
  }

  function loadEnqueteursFiltre() {
    const date   = $('#filter-date').val();
    const isAero = $('#filter-type-site').val() === 'AEROPORT';
    const params = { date };
    let url;
    if (isAero) {
      url = '/api/enqueteurs/aeroport/';
      const idAero = $('#filter-aeroport').val();
      if (idAero) params.id_aeroport = idAero;
    } else {
      url = '/api/enqueteurs/site/';
      const idSite = $('#filter-site').val();
      if (idSite) params.id_site = idSite;
    }
    $.get(url, params).done(function (resp) {
      if (resp.status !== 'ok') return;
      const $sel = $('#filter-enqueteur');
      const prev = $sel.val() || sessionStorage.getItem('ever.affectation.enqueteur');
      $sel.find('option:not(:first)').remove();
      resp.data.forEach(e => $sel.append(
        `<option value="${e.Id_Personne}">${escHtml(e.Libelle_Enqueteur)}</option>`
      ));
      if (prev) $sel.val(prev);
    });
  }

  // ── Chargement des vacations ──────────────────────────────────────────────
  function loadData() {
    showSpinner();
    resetSelection();
    const isAero = $('#filter-type-site').val() === 'AEROPORT';
    const params = {
      date:        $('#filter-date').val(),
      type_site:   isAero ? 'AEROPORT' : 'HORS',
      id_aeroport: isAero ? ($('#filter-aeroport').val() || '') : '',
      id_site:     !isAero ? ($('#filter-site').val() || '') : '',
      id_personne: $('#filter-enqueteur').val() || '',
    };
    $.get('/api/affectation/vacations/', params)
    .done(function (resp) {
      if (resp.status !== 'ok') { showError(resp.message); return; }
      renderTable(resp.data);
      markRefresh();
    })
    .fail(() => showError('Erreur réseau.'))
    .always(hideSpinner);
  }

  // ── Rendu du tableau ──────────────────────────────────────────────────────
  function renderTable(rows) {
    const $tbody = $('#tbody-affectation').empty();
    $('#panel-detail-vacation').addClass('d-none');

    if (!rows || rows.length === 0) {
      $('#unassigned-alert').addClass('d-none');
      document.title = 'EVER 2026 – Affectation';
      $tbody.append('<tr><td colspan="13" class="text-center text-muted py-4">Aucune vacation pour ces critères.</td></tr>');
      return;
    }

    rows.sort((a, b) => {
      const site = (a.Nom_Site_Ou_Aeroport || '').localeCompare(b.Nom_Site_Ou_Aeroport || '', 'fr');
      return site !== 0 ? site : (a.Heure_Arrivee_Enqueteur || '').localeCompare(b.Heure_Arrivee_Enqueteur || '');
    });

    const nbNonAffectees = rows.filter(r => !r.ID_Personne_1).length;
    if (nbNonAffectees > 0) {
      $('#unassigned-count-text').text(
        `${nbNonAffectees} vacation${nbNonAffectees > 1 ? 's' : ''} sans enquêteur affecté`
      );
      $('#unassigned-alert').removeClass('d-none');
      document.title = `⚠️ ${nbNonAffectees} – Affectation`;
    } else {
      $('#unassigned-alert').addClass('d-none');
      document.title = 'EVER 2026 – Affectation';
    }

    rows.forEach(function (r) {
      const modifiable = !!r.Affectation_Modifiable;
      const isZone     = r.ID_Vacation_1 !== undefined;
      const vac1   = isZone ? r.ID_Vacation_1 : r.ID_Vacation;
      const vac2   = r.ID_Vacation_2 || null;
      const vType  = isZone ? 'ZONE' : 'AEROPORT';
      const isComplete = r.Nbre_Interviews_Realisees >= r.Nbre_Interviews_A_Faire
                         && r.Nbre_Interviews_A_Faire > 0;

      const detailBtn = isZone
        ? `<button class="btn btn-sm btn-outline-secondary btn-detail"
               data-id="${r.ID_Vacation}" data-num="${r.Numero_Vacation || ''}"
               title="Détail"><i class="bi bi-list-ul"></i></button>`
        : '';

      const cmntBtn = `<button class="btn-comment ${r.Commentaire_Avant || r.Commentaire_Apres ? 'has-comment' : ''}"
          data-id="${r.ID_Vacation}" data-num="${r.Numero_Vacation || ''}"
          data-vac1="${escHtml(r.Commentaire_Avant || '')}" data-vol1="${escHtml(r.Commentaire_Apres || '')}"
          data-vac2="" data-vol2="" title="Commentaire"><i class="bi bi-chat-left-text"></i></button>`;

      const rowCls = [
        'row-vacation assign-row',
        isComplete                         ? 'row-complete'       : '',
        !r.ID_Personne_1 && modifiable     ? 'row-unassigned'     : '',
        !modifiable                        ? 'row-non-modifiable' : '',
      ].filter(Boolean).join(' ');

      const enq1Html = slotText(r.ID_Personne_1, r.Libelle_Enqueteur_1, modifiable);
      const enq2Html = vac2
        ? slotText(r.ID_Personne_2, r.Libelle_Enqueteur_2, modifiable)
        : '<span class="text-muted">—</span>';

      $tbody.append(`<tr class="${rowCls}"
          data-vac1="${vac1 || ''}"
          data-pers1="${r.ID_Personne_1 || ''}"
          data-vac2="${vac2 || ''}"
          data-pers2="${r.ID_Personne_2 || ''}"
          data-modifiable="${modifiable ? '1' : '0'}"
          data-type="${vType}"
          data-id="${r.ID_Vacation}">
        <td>${escHtml(r.Nom_Site_Ou_Aeroport || '')}</td>
        <td>${escHtml(fmtDate(r.Date_Vacation) || '')}</td>
        <td class="cell-code">${escHtml(r.Code_Periode_Journee || '')}</td>
        <td class="cell-code">${escHtml(r.Numero_Vacation || '')}</td>
        <td>${escHtml(r.Heure_Arrivee_Enqueteur || '')}</td>
        <td>${escHtml(r.Heure_Depart_Enqueteur || '')}</td>
        <td class="text-end">${r.Nbre_Interviews_A_Faire ?? '—'}</td>
        <td class="text-end">${r.Nbre_Interviews_Realisees ?? '—'}</td>
        <td class="text-end">${r.Nbre_Interviews_Valides ?? '—'}</td>
        <td class="slot-enq1">${enq1Html}</td>
        <td class="slot-enq2">${enq2Html}</td>
        <td class="text-center">${detailBtn}</td>
        <td class="text-center">${cmntBtn}</td>
      </tr>`);
    });
  }

  function slotText(idPersonne, libelle, modifiable) {
    if (libelle) {
      const cls = modifiable ? 'text-primary fw-medium' : 'text-secondary';
      return `<span class="${cls}">${escHtml(libelle)}</span>`;
    }
    return `<span class="text-muted fst-italic">Non affecté</span>`;
  }

  // ── Clic sur une ligne (pattern DGAC) ────────────────────────────────────
  $('#tbody-affectation').on('click', 'tr.assign-row', function (e) {
    if ($(e.target).closest('button, a').length) return;
    e.stopPropagation();
    $('.ever-enq-dropdown').hide();

    if ($selectedRow) {
      closeAndReload();
      return;
    }

    openRow($(this));
  });

  function openRow($tr) {
    const doOpen = function () {
      savedScrollTop = $('.ever-table-scroll').scrollTop();
      $selectedRow = $tr.addClass('assign-selected');
      $tr.siblings('tr').addClass('assign-hidden');

      // Superviseurs (§4.8) : accès en lecture uniquement, quel que soit
      // Affectation_Modifiable renvoyé par la TVF.
      const modifiable = CAN_MODIFY_AFFECTATION && parseInt($tr.data('modifiable')) === 1;

      if (modifiable) {
        const vac1  = $tr.data('vac1')  || null;
        const pers1 = $tr.data('pers1') || null;
        const vac2  = $tr.data('vac2')  || null;
        const pers2 = $tr.data('pers2') || null;
        const vType = $tr.data('type') || 'AEROPORT';
        if (vac1) buildEnqDropdown($tr.find('.slot-enq1'), parseInt(vac1),  pers1 ? parseInt(pers1) : null, vType);
        if (vac2) buildEnqDropdown($tr.find('.slot-enq2'), parseInt(vac2),  pers2 ? parseInt(pers2) : null, vType);
      } else {
        $tr.find('.slot-enq1, .slot-enq2')
           .attr('title', 'Vacation non modifiable')
           .css('cursor', 'not-allowed');
      }
    };

    doOpen();
  }

  function resetSelection() {
    if ($selectedRow) {
      $selectedRow.siblings('tr').removeClass('assign-hidden');
      $selectedRow.removeClass('assign-selected');
      $selectedRow = null;
    }
    // Supprimer les menus attachés au body
    $('.ever-enq-dropdown').remove();
  }

  function closeAndReload() {
    if (isSavingAffect) return;
    resetSelection();
    loadData();
  }

  // Clic hors tableau → fermer
  $(document).on('click', function (e) {
    if (!$selectedRow) return;
    if ($(e.target).closest('#table-affectation, .ever-filters, #modal-password').length) return;
    closeAndReload();
  });

  // ── Dropdown personnalisé par slot ───────────────────────────────────────
  // Le $menu est attaché au <body> avec position:fixed pour échapper aux
  // overflow:auto des conteneurs de tableau (sinon la liste est coupée).
  function buildEnqDropdown($td, idVacEnq, idPers, vType) {
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

    // Menu attaché au body pour ne pas être coupé par overflow du tableau
    const $menu = $('<div class="ever-enq-dropdown"></div>')
      .append('<div class="dropdown-item small py-1" data-id="">— Non affecté —</div>')
      .appendTo('body');

    $.get('/api/affectation/enqueteurs-pour-vacation/', { id_vacation: idVacEnq, type: vType })
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
      const candidats = vType === 'ZONE'
        ? resp.data.filter(e => !e.Affecte_Vacation || e.Id_Personne === idPers)
        : resp.data;

      candidats.forEach(function (item) {
        const star = item.Affecte_Vacation
          ? ' <small class="text-warning" title="Déjà affecté à cet horaire">★</small>'
          : '';
        $menu.append(
          `<div class="dropdown-item small py-1" data-id="${item.Id_Personne}">${escHtml(item.Libelle_Enqueteur)}${star}</div>`
        );
      });
      const current = idPers ? candidats.find(e => e.Id_Personne === idPers) : null;
      $input.val(current ? current.Libelle_Enqueteur : '').attr('placeholder', 'Non affecté');
      $td.data('sel-id', idPers || null);
    })
    .fail(function () {
      $td.html('<span class="text-danger small">Erreur réseau</span>');
      $menu.remove();
    });

    // Toggle : positionne le menu en fixed sous le groupe input
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

    // Sélection d'un item
    $menu.on('click', '.dropdown-item', function (e) {
      e.stopPropagation();
      const newId   = $(this).data('id') || null;
      const newText = $(this).text().replace('★', '').trim();
      $menu.hide();
      if ($td.data('sel-id') == newId) return;
      setEnqueteur(idVacEnq, newId, newText, $td);
    });
  }

  // Fermeture des dropdowns au clic global
  $(document).on('click', function () {
    $('.ever-enq-dropdown').hide();
  });

  // ── Sauvegarde affectation ─────────────────────────────────────────────────
  function setEnqueteur(idVacEnq, idPersonne, text, $td) {
    isSavingAffect = true;
    $('body').css('cursor', 'wait');

    const realId = idPersonne ? parseInt(idPersonne) : null;
    const type   = $selectedRow ? ($selectedRow.data('type') || 'AEROPORT') : 'AEROPORT';

    ajaxPost('/api/affectation/set/', { id_vacation: idVacEnq, id_personne: realId, type })
    .done(function (resp) {
      if (resp.status !== 'ok') {
        alert('Erreur affectation : ' + (resp.message || ''));
      } else {
        $td.find('.ever-enq-input').val(text);
        $td.data('sel-id', realId);
      }
    })
    .fail(function () {
      alert('Erreur réseau lors de l\'affectation.');
    })
    .always(function () {
      isSavingAffect = false;
      $('body').css('cursor', 'default');
    });
  }

  // ── Détail vacation (hors-aéroport) ──────────────────────────────────────
  $(document).on('click', '.btn-detail', function (e) {
    e.stopPropagation();
    const idVacation = $(this).data('id');
    const num        = $(this).data('num');
    showSpinner();
    $.get('/api/suivi/hors-aeroport/detail/', { id_vacation: idVacation })
    .done(function (resp) {
      if (resp.status !== 'ok') { alert('Erreur chargement détail.'); return; }
      renderDetail(num, resp.data);
    })
    .fail(() => alert('Erreur réseau.'))
    .always(hideSpinner);
  });

  function renderDetail(num, rows) {
    $('#detail-vacation-num').text(num);
    let html = '';
    if (!rows || rows.length === 0) {
      html = '<p class="text-muted">Aucun détail disponible.</p>';
    } else {
      html = `<table class="ever-table">
        <thead><tr>
          <th>Site</th><th>Type</th><th>Enquêteur</th>
          <th class="text-end">Objectif</th>
          <th class="text-end">Recrutés</th>
          <th class="text-end">Valides</th>
          <th class="text-end">Abandons</th>
        </tr></thead><tbody>`;
      rows.forEach(r => {
        html += `<tr>
          <td>${escHtml(r.Nom_Site||'')}</td>
          <td>${escHtml(r.Type_Site||r.Code_Type_Site||'')}</td>
          <td>${escHtml(r.Libelle_Enqueteur||'')}</td>
          <td class="text-end">${r.Objectif_Total??'—'}</td>
          <td class="text-end">${r.Recrutes??'—'}</td>
          <td class="text-end">${r.Valides??'—'}</td>
          <td class="text-end">${r.Abandons??'—'}</td>
        </tr>`;
      });
      html += '</tbody></table>';
    }
    $('#detail-vacation-content').html(html);
    $('#panel-detail-vacation').removeClass('d-none');
    $('html, body').animate({ scrollTop: $('#panel-detail-vacation').offset().top - 20 }, 300);
  }

  // ── Utilitaires ───────────────────────────────────────────────────────────
  function showError(msg) {
    $('#tbody-affectation').html(
      `<tr><td colspan="13" class="text-center text-danger py-4">
        <i class="bi bi-exclamation-triangle me-2"></i>${escHtml(msg||'Erreur')}
      </td></tr>`
    );
  }

  function escHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

});
