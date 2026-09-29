/**
 * vacations_zone.js — Vacations Zone / Affectation, Solutions Terrain (v1.1, §7.3)
 * Source SQL :
 *   - liste     : ft_Extranet_Vacation_Zone_Pivot (déjà livrée par Philippe)
 *   - détail    : ft_EVER_Tableau_Zone_Site_Chef_Equipe (réutilisée du suivi zones)
 *   - création  : Prc_Vacation_Zone_Insert (déjà livrée le 18/08 par Philippe)
 *
 * Affectation des enquêteurs : câblée ici depuis le 2026-09-29, conformément à
 * la règle 05 (« Lors du clic sur une ligne, la fonctionnalité affectation est
 * activée »). Elle s'appuie sur ft_EVER_Liste_Enqueteur_Pour_Affectation_Zone,
 * livrée par Philippe le 23/09. Le menu lui-même est partagé avec l'écran
 * Affectation : voir static/js/enq_dropdown.js.
 */
$(function () {

  let zonesCache = [];
  let lastRows   = [];   // dernières lignes chargées, pour l'export CSV

  // ---- Datepickers (2 champs : Date début / Date fin — cf. commentaire Word
  // de Nicolas sur "Dates Sélection", §7.3.1) — l'init globale d'ever.js ne
  // couvre que #filter-date, donc on initialise ici les 2 champs propres à
  // cet écran, avec la même config (calendrier only, anti-autofill).
  // Les deux bornes sont solidaires : choisir une date de début postérieure à la
  // date de fin n'affichait aucune ligne, sans rien expliquer à l'écran (remonté
  // par Nicolas le 29/09). La borne qui deviendrait incohérente suit donc celle
  // que l'utilisateur vient de choisir.
  function accorderBornes(selModifie) {
    const debut = document.querySelector('#filter-date-debut')?._flatpickr;
    const fin   = document.querySelector('#filter-date-fin')?._flatpickr;
    if (!debut || !fin || !debut.selectedDates[0] || !fin.selectedDates[0]) return;
    if (debut.selectedDates[0] <= fin.selectedDates[0]) return;
    if (selModifie === '#filter-date-debut') fin.setDate(debut.selectedDates[0], false);
    else                                     debut.setDate(fin.selectedDates[0], false);
  }

  function initDatepicker(sel) {
    if (!document.querySelector(sel)) return;
    flatpickr(sel, {
      locale: 'fr', dateFormat: 'Y-m-d', altInput: true, altFormat: 'd/m/Y',
      allowInput: false,
      onChange() { accorderBornes(sel); },
      onReady(selectedDates, dateStr, instance) {
        if (instance.altInput) {
          instance.altInput.setAttribute('autocomplete', 'off');
          instance.altInput.setAttribute('name', sel.replace('#', '') + '-display');
          instance.altInput.setAttribute('readonly', 'readonly');
          instance.altInput.setAttribute('data-lpignore', 'true');
          instance.altInput.setAttribute('data-form-type', 'other');
          instance.altInput.setAttribute('data-1p-ignore', 'true');
        }
      },
    });
  }
  initDatepicker('#filter-date-debut');
  initDatepicker('#filter-date-fin');

  function setDate(sel, isoDate) {
    if (!isoDate) return;
    const fp = document.querySelector(sel)?._flatpickr;
    if (fp) fp.setDate(isoDate, false);
    else $(sel).val(isoDate);
  }

  // ---- Persistance des filtres ----
  const FS = {
    save() {
      sessionStorage.setItem('ever.vacz.date_debut', $('#filter-date-debut').val());
      sessionStorage.setItem('ever.vacz.date_fin', $('#filter-date-fin').val());
      sessionStorage.setItem('ever.vacz.zone', $('#filter-zone').val());
      sessionStorage.setItem('ever.vacz.enqueteur', $('#filter-enqueteur').val());
    },
    restore() {
      setDate('#filter-date-debut', sessionStorage.getItem('ever.vacz.date_debut'));
      setDate('#filter-date-fin', sessionStorage.getItem('ever.vacz.date_fin'));
    },
  };
  FS.restore();

  loadZones().then(function () {
    const prevZone = sessionStorage.getItem('ever.vacz.zone');
    if (prevZone) $('#filter-zone').val(prevZone);
  });
  loadEnqueteurs().then(function () {
    const prevEnq = sessionStorage.getItem('ever.vacz.enqueteur');
    if (prevEnq) $('#filter-enqueteur').val(prevEnq);
  });
  loadData();

  $('#filter-date-debut, #filter-date-fin, #filter-zone, #filter-enqueteur').on('change', function () {
    FS.save();
    loadData();
  });
  $('#btn-refresh-data').on('click', loadData);
  $('#btn-close-detail').on('click', () => $('#panel-detail-vacation').addClass('d-none'));

  // "Aujourd'hui" : remet les 2 dates sur la date du jour (le handler global
  // d'ever.js cible #filter-date, absent ici, donc no-op — celui-ci fait le travail réel).
  $(document).on('click', '#btn-today', function () {
    const today = new Date().toISOString().split('T')[0];
    const fpDebut = document.querySelector('#filter-date-debut')?._flatpickr;
    const fpFin   = document.querySelector('#filter-date-fin')?._flatpickr;
    if (fpDebut) fpDebut.setDate(today, true);
    if (fpFin) fpFin.setDate(today, true);
  });

  // ---- Référentiels ----
  function loadZones() {
    return $.get('/api/zones-enquete/').then(function (resp) {
      if (resp.status !== 'ok') return;
      zonesCache = resp.data || [];
      const $sel = $('#filter-zone');
      $sel.find('option:not(:first)').remove();
      zonesCache.forEach(z => $sel.append(`<option value="${z.ID_Zone_Enquete}">${escHtml(z.Zone_Enquete)}</option>`));
    });
  }

  function loadEnqueteurs() {
    return $.get('/api/enqueteurs-terrain/').then(function (resp) {
      if (resp.status !== 'ok') return;
      const $sel = $('#filter-enqueteur');
      $sel.find('option:not(:first)').remove();
      (resp.data || []).forEach(e => $sel.append(
        `<option value="${e.ID_Enqueteur_Terrain}">${escHtml(e.Matricule_Enqueteur_Terrain)} - ${escHtml(e.Nom)} ${escHtml(e.Prenom)}</option>`
      ));
    });
  }

  // ---- Liste des vacations ----
  function loadData() {
    showSpinner();
    const params = {
      date_debut:      $('#filter-date-debut').val(),
      date_fin:        $('#filter-date-fin').val(),
      id_zone_enquete: $('#filter-zone').val()       || '',
      id_enqueteur:    $('#filter-enqueteur').val()  || '',
    };
    $.get('/api/vacations-zone/', params)
    .done(function (resp) {
      if (resp.status !== 'ok') { showError(resp.message); return; }
      lastRows = resp.data || [];
      $('#btn-export-csv').prop('disabled', lastRows.length === 0);
      renderTable(lastRows);
      markRefresh();
    })
    .fail(() => showError('Erreur réseau.'))
    .always(hideSpinner);
  }

  function renderTable(rows) {
    const $tbody = $('#tbody-vacations-zone').empty();
    $('#panel-detail-vacation').addClass('d-none');

    if (!rows.length) {
      $tbody.append('<tr><td colspan="5" class="text-center text-muted py-4">Aucune vacation pour ces critères.</td></tr>');
      return;
    }

    rows.forEach(function (r) {
      const detailBtn = r.ID_Vacation_Zone_1
        ? `<button class="btn btn-sm btn-outline-secondary btn-detail"
             data-id="${r.ID_Vacation_Zone_1}" data-num="${r.Numero_Vacation || ''}"
             title="Voir les sites"><i class="bi bi-list-ul"></i></button>`
        : '<span class="text-muted">—</span>';

      const modifiable = CAN_MODIFY_AFFECTATION && r.Affectation_Modifiable;

      $tbody.append(`<tr class="row-vacation${modifiable ? ' assign-row' : ''}"
          data-vac1="${r.ID_Vacation_Zone_1 || ''}"
          data-pers1="${r.ID_Personne_1 || ''}"
          data-vac2="${r.ID_Vacation_Zone_2 || ''}"
          data-pers2="${r.ID_Personne_2 || ''}"
          data-modifiable="${modifiable ? '1' : '0'}">
        <td>${escHtml(r.Zone_Enquete || '')}${r.Vacation_Rattrapage ? ' <span class="badge bg-warning text-dark">Rattrapage</span>' : ''}</td>
        <td class="cell-code">${escHtml(r.Numero_Vacation || '')}</td>
        <td class="slot-enq1">${r.Libelle_Enqueteur_1 ? escHtml(r.Libelle_Enqueteur_1) : '<span class="text-muted">— à affecter —</span>'}</td>
        <td class="slot-enq2">${r.ID_Vacation_Zone_2 ? (r.Libelle_Enqueteur_2 ? escHtml(r.Libelle_Enqueteur_2) : '<span class="text-muted">— à affecter —</span>') : '<span class="text-muted">—</span>'}</td>
        <td class="text-center">${detailBtn}</td>
      </tr>`);
    });
  }

  // ---- Détail des sites ----
  // ── Affectation depuis la liste (specs §7.3, règle 05) ───────────────────
  // Un clic sur une ligne ouvre les menus de sélection d'enquêteur ; un clic
  // ailleurs referme et recharge, pour que la liste reflète les affectations
  // faites (et que les enquêteurs devenus indisponibles disparaissent des menus).
  let $ligneOuverte = null;
  let enCoursDeSauvegarde = false;

  function fermerLigne(recharger) {
    if (!$ligneOuverte) return;
    $('.ever-enq-dropdown').remove();
    $ligneOuverte.removeClass('assign-selected');
    $ligneOuverte = null;
    if (recharger) loadData();
  }

  $('#tbody-vacations-zone').on('click', 'tr.assign-row', function (e) {
    if ($(e.target).closest('button, a, .ever-enq-wrap').length) return;
    e.stopPropagation();
    if ($ligneOuverte) { fermerLigne(true); return; }

    const $tr   = $(this).addClass('assign-selected');
    $ligneOuverte = $tr;

    const vac1  = $tr.data('vac1')  || null;
    const pers1 = $tr.data('pers1') || null;
    const vac2  = $tr.data('vac2')  || null;
    const pers2 = $tr.data('pers2') || null;

    const options = {
      type:        'ZONE',
      onSaveStart: function () { enCoursDeSauvegarde = true; },
      onSaveEnd:   function () { enCoursDeSauvegarde = false; },
    };
    if (vac1) EverEnqDropdown.build($tr.find('.slot-enq1'),
      Object.assign({ idVacation: parseInt(vac1), idPersonne: pers1 ? parseInt(pers1) : null }, options));
    if (vac2) EverEnqDropdown.build($tr.find('.slot-enq2'),
      Object.assign({ idVacation: parseInt(vac2), idPersonne: pers2 ? parseInt(pers2) : null }, options));
  });

  $(document).on('click', function (e) {
    if (!$ligneOuverte || enCoursDeSauvegarde) return;
    if ($(e.target).closest('#table-vacations-zone, .ever-filters, .ever-enq-dropdown, .modal').length) return;
    fermerLigne(true);
  });

  $(document).on('click', '.btn-detail', function () {
    const idVacation = $(this).data('id');
    const num = $(this).data('num');
    showSpinner();
    $.get('/api/vacations-zone/detail/', { id_vacation: idVacation })
    .done(function (resp) {
      if (resp.status !== 'ok') { alert('Erreur chargement détail.'); return; }
      renderDetail(num, resp.data);
    })
    .fail(() => alert('Erreur réseau.'))
    .always(hideSpinner);
  });

  function renderDetail(num, rows) {
    $('#detail-vacation-num').text(num);
    const $tbody = $('#tbody-detail-sites').empty();
    if (!rows.length) {
      $tbody.append('<tr><td colspan="2" class="text-center text-muted">Aucun site.</td></tr>');
    } else {
      rows.forEach(function (r) {
        const typeBadge = r.Sites_Autres
          ? '<span class="badge bg-light text-dark border">Autres sites</span>'
          : `<span class="badge bg-secondary">${escHtml(r.Type_Site || '')}</span>`;
        $tbody.append(`<tr><td>${escHtml(r.Nom_Site || '')}</td><td>${typeBadge}</td></tr>`);
      });
    }
    $('#panel-detail-vacation').removeClass('d-none');
    $('html, body').animate({ scrollTop: $('#panel-detail-vacation').offset().top - 20 }, 300);
  }

  // ---- Création ----
  const modalCreation = new bootstrap.Modal('#modal-creation-vacation');

  $('#btn-creer-vacation').on('click', function () {
    $('#creation-lignes').empty();
    $('#creation-error').addClass('d-none').text('');
    ajouterLigne();
    modalCreation.show();
  });

  $('#btn-ajouter-ligne').on('click', ajouterLigne);

  function ajouterLigne() {
    const tplNode = document.getElementById('template-ligne-creation').content.cloneNode(true);
    const $ligne  = $(tplNode.querySelector('.ligne-creation'));
    const $sel    = $ligne.find('.ligne-zone');
    zonesCache.forEach(z => $sel.append(`<option value="${z.ID_Zone_Enquete}">${escHtml(z.Zone_Enquete)}</option>`));
    $('#creation-lignes').append($ligne);
  }

  $(document).on('click', '.btn-supprimer-ligne', function () {
    if ($('#creation-lignes .ligne-creation').length > 1) {
      $(this).closest('.ligne-creation').remove();
    }
  });

  $('#btn-valider-creation').on('click', function () {
    const lignes = [];
    let manquant = false;
    $('#creation-lignes .ligne-creation').each(function () {
      const d = $(this).find('.ligne-date').val();
      const z = $(this).find('.ligne-zone').val();
      $(this).find('.ligne-date, .ligne-zone').removeClass('is-invalid');
      const nb = parseInt($(this).find('.ligne-nb-enqueteurs').val()) || 1;
      if (!d) { $(this).find('.ligne-date').addClass('is-invalid'); manquant = true; }
      if (!z) { $(this).find('.ligne-zone').addClass('is-invalid'); manquant = true; }
      if (d && z) lignes.push({ date_vacation: d, id_zone_enquete: parseInt(z), nombre_enqueteurs: nb });
    });

    $('#creation-error').addClass('d-none').text('');
    if (manquant) {
      showCreationError('Informations manquantes : Date et Zone sont obligatoires pour chaque ligne.');
      return;
    }

    const today = new Date().toISOString().split('T')[0];
    if (lignes.some(l => l.date_vacation <= today)) {
      showCreationError('Les dates des vacations doivent être supérieures à la date du jour.');
      return;
    }

    showSpinner();
    ajaxPost('/api/vacations-zone/create/', { lignes })
    .done(function (resp) {
      if (resp.status === 'ok') {
        modalCreation.hide();
        loadData();
      } else {
        showCreationError(resp.message || 'Erreur lors de la création.');
      }
    })
    .fail(function (xhr) {
      const msg = xhr.responseJSON && xhr.responseJSON.message
        ? xhr.responseJSON.message
        : 'Erreur réseau lors de la création.';
      showCreationError(msg);
    })
    .always(hideSpinner);
  });

  function showCreationError(msg) {
    $('#creation-error').removeClass('d-none').text(msg);
  }

  // ---- Export CSV ----
  // Colonnes confirmées par Nicolas (mail du 2026-08-20, point 13) : Date,
  // Id zone, nom de la zone, Code enquêteur, nom prénom enquêteur affecté.
  // Une ligne par enquêteur affecté ; une ligne à blanc si la vacation n'a
  // encore aucun enquêteur (pour ne pas la faire disparaître de l'export).
  $('#btn-export-csv').on('click', function () {
    if (!lastRows || lastRows.length === 0) return;

    const headers = ['Date', 'Id zone', 'Nom de la zone', 'Code enquêteur', 'Nom prénom enquêteur affecté'];
    const csvRows = [headers.join(';')];

    function addRow(r, matricule, nom, prenom) {
      const row = [
        fmtDate(r.Date_Vacation),
        r.ID_Zone_Enquete ?? '',
        r.Zone_Enquete || '',
        matricule || '',
        (nom || prenom) ? `${nom || ''} ${prenom || ''}`.trim() : '',
      ].map(function (v) {
        const s = String(v);
        return s.includes(';') || s.includes('"') || s.includes('\n')
          ? '"' + s.replace(/"/g, '""') + '"'
          : s;
      });
      csvRows.push(row.join(';'));
    }

    lastRows.forEach(function (r) {
      const has1 = !!r.Matricule_Enqueteur_1;
      const has2 = !!r.Matricule_Enqueteur_2;
      if (has1) addRow(r, r.Matricule_Enqueteur_1, r.Nom_Enqueteur_1, r.Prenom_Enqueteur_1);
      if (has2) addRow(r, r.Matricule_Enqueteur_2, r.Nom_Enqueteur_2, r.Prenom_Enqueteur_2);
      if (!has1 && !has2) addRow(r, '', '', '');
    });

    const dateExport = $('#filter-date-debut').val() || 'export';
    const bom  = '﻿';   // BOM UTF-8 pour Excel FR
    const blob = new Blob([bom + csvRows.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `vacations_zone_${dateExport}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  });

  function showError(msg) {
    $('#tbody-vacations-zone').html(
      `<tr><td colspan="5" class="text-center text-danger py-4">
        <i class="bi bi-exclamation-triangle me-2"></i>${escHtml(msg)}
      </td></tr>`
    );
  }

  function escHtml(str) {
    return String(str ?? '')
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

});
