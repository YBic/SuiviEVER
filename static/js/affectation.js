/**
 * affectation.js — Affectation des enquêteurs aux vacations
 */

$(function () {

  let allEnqueteurs = [];
  let isAuthorized = false;

  // ---- Init ----
  loadEnqueteursListe();
  loadSitesEtAeroports();
  loadData();

  // ---- Bascule aéroport / hors aéroport ----
  $('#filter-type-site').on('change', function () {
    const isAero = $(this).val() === 'AEROPORT';
    $('#group-aeroport').toggleClass('d-none', !isAero);
    $('#group-site').toggleClass('d-none', isAero);
    loadSitesEtAeroports();
    loadData();
  });

  $('#filter-date, #filter-aeroport, #filter-site, #filter-enqueteur').on('change', loadData);
  $('#btn-refresh-data').on('click', loadData);
  $('#btn-close-detail').on('click', () => $('#panel-detail-vacation').addClass('d-none'));

  function loadSitesEtAeroports() {
    const date = $('#filter-date').val();
    const isAero = $('#filter-type-site').val() === 'AEROPORT';
    if (isAero) {
      $.get('/api/aeroports/', { date }).done(function (resp) {
        if (resp.status !== 'ok') return;
        const $sel = $('#filter-aeroport');
        const prev = $sel.val();
        $sel.find('option:not(:first)').remove();
        resp.data.forEach(a => $sel.append(`<option value="${a.Id_Aeroport}">${a.Code_Aeroport} – ${a.Nom_Aeroport}</option>`));
        if (prev) $sel.val(prev);
      });
    } else {
      $.get('/api/sites/', { date }).done(function (resp) {
        if (resp.status !== 'ok') return;
        const $sel = $('#filter-site');
        const prev = $sel.val();
        $sel.find('option:not(:first)').remove();
        resp.data.forEach(s => $sel.append(`<option value="${s.Id_Site}">[${s.Type_Site}] ${s.Nom_Site}</option>`));
        if (prev) $sel.val(prev);
      });
    }
  }

  function loadEnqueteursListe() {
    $.get('/api/affectation/enqueteurs/')
    .done(function (resp) {
      if (resp.status !== 'ok') return;
      allEnqueteurs = resp.data;
      // Peupler filtre enquêteur
      const $sel = $('#filter-enqueteur');
      allEnqueteurs.forEach(e => $sel.append(`<option value="${e.Id_Personne}">${e.Libelle_Enqueteur}</option>`));
    });
  }

  function loadData() {
    showSpinner();
    const isAero = $('#filter-type-site').val() === 'AEROPORT';
    const params = {
      date:        $('#filter-date').val(),
      id_aeroport: isAero ? ($('#filter-aeroport').val() || '') : '',
      id_site:     !isAero ? ($('#filter-site').val() || '') : '',
      id_personne: $('#filter-enqueteur').val() || '',
    };

    $.get('/api/affectation/vacations/', params)
    .done(function (resp) {
      if (resp.status !== 'ok') { showError(resp.message); return; }
      renderTable(resp.data);
    })
    .fail(() => showError('Erreur réseau.'))
    .always(hideSpinner);
  }

  // ---- Rendu du tableau ----
  function renderTable(rows) {
    const $tbody = $('#tbody-affectation').empty();
    $('#panel-detail-vacation').addClass('d-none');

    if (!rows || rows.length === 0) {
      $tbody.append('<tr><td colspan="13" class="text-center text-muted py-4">Aucune vacation pour ces critères.</td></tr>');
      return;
    }

    rows.forEach(function (r) {
      const modifiable = r.Affectation_Modifiable;
      const isComplete = r.Nbre_Interviews_Realisees >= r.Nbre_Interviews_A_Faire && r.Nbre_Interviews_A_Faire > 0;

      const cmntBtn = `<button class="btn-comment ${r.Commentaire_Avant || r.Commentaire_Apres ? 'has-comment' : ''}"
        data-id="${r.ID_Vacation}" data-num="${r.Numero_Vacation || ''}"
        data-avant="${escHtml(r.Commentaire_Avant || '')}"
        data-apres="${escHtml(r.Commentaire_Apres || '')}"
        title="Commentaire"><i class="bi bi-chat-left-text"></i></button>`;

      const detailBtn = `<button class="btn btn-sm btn-outline-secondary btn-detail"
        data-id="${r.ID_Vacation}" data-num="${r.Numero_Vacation || ''}"
        title="Détail"><i class="bi bi-list-ul"></i></button>`;

      $tbody.append(`<tr class="row-vacation ${isComplete ? 'row-complete' : ''}" data-id="${r.ID_Vacation}">
        <td>${escHtml(r.Nom_Site_Ou_Aeroport || '')}</td>
        <td>${escHtml(fmtDate(r.Date_Vacation) || '')}</td>
        <td class="cell-code">${escHtml(r.Code_Periode_Journee || '')}</td>
        <td class="cell-code">${escHtml(r.Numero_Vacation || '')}</td>
        <td>${escHtml(r.Heure_Arrivee_Enqueteur || '')}</td>
        <td>${escHtml(r.Heure_Depart_Enqueteur || '')}</td>
        <td class="text-end">${r.Nbre_Interviews_A_Faire ?? '—'}</td>
        <td class="text-end">${r.Nbre_Interviews_Realisees ?? '—'}</td>
        <td class="text-end">${r.Nbre_Interviews_Valides ?? '—'}</td>
        <td>${buildEnqueteurSelect(r.ID_Vacation, 1, r.ID_Personne_1, modifiable)}</td>
        <td>${buildEnqueteurSelect(r.ID_Vacation, 2, r.ID_Personne_2, modifiable)}</td>
        <td class="text-center">${detailBtn}</td>
        <td class="text-center">${cmntBtn}</td>
      </tr>`);
    });
  }

  function buildEnqueteurSelect(idVacation, rang, idPersonne, modifiable) {
    const disabled = modifiable ? '' : 'disabled';
    let options = '<option value="">— Non affecté —</option>';
    allEnqueteurs.forEach(function (e) {
      const sel = e.Id_Personne == idPersonne ? 'selected' : '';
      options += `<option value="${e.Id_Personne}" ${sel}>${escHtml(e.Libelle_Enqueteur)}</option>`;
    });
    return `<select class="affectation-select" ${disabled}
      data-vacation="${idVacation}" data-rang="${rang}">${options}</select>`;
  }

  // ---- Sauvegarde affectation ----
  $(document).on('change', '.affectation-select', function () {
    const $sel = $(this);
    const idVacation = $sel.data('vacation');
    const rang       = $sel.data('rang');
    const idPersonne = $sel.val() || null;

    const doSave = function () {
      showSpinner();
      ajaxPost('/api/affectation/set/', {
        id_vacation: idVacation,
        rang:        rang,
        id_personne: idPersonne ? parseInt(idPersonne) : null,
      })
      .done(function (resp) {
        if (resp.status !== 'ok') {
          alert('Erreur lors de l\'affectation : ' + (resp.message || ''));
          loadData(); // recharger pour annuler le changement visuel
        }
      })
      .fail(function () {
        alert('Erreur réseau lors de l\'affectation.');
        loadData();
      })
      .always(hideSpinner);
    };

    if (!isAuthorized) {
      checkAffectationPassword(function () {
        isAuthorized = true;
        doSave();
      });
    } else {
      doSave();
    }
  });

  // ---- Détail vacation ----
  $(document).on('click', '.btn-detail', function () {
    const idVacation = $(this).data('id');
    const num = $(this).data('num');
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
          <th>Site</th><th>Type</th>
          <th class="text-end">100% complétés</th>
          <th class="text-end">Recrutés</th>
          <th class="text-end">Valides</th>
          <th class="text-end">Abandons</th>
        </tr></thead><tbody>`;
      rows.forEach(r => {
        html += `<tr>
          <td>${escHtml(r.Nom_Site||'')}</td>
          <td>${escHtml(r.Type_Site||'')}</td>
          <td class="text-end">${r.Completes_100??'—'}</td>
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

  function showError(msg) {
    $('#tbody-affectation').html(
      `<tr><td colspan="13" class="text-center text-danger py-4">
        <i class="bi bi-exclamation-triangle me-2"></i>${escHtml(msg||'Erreur')}
      </td></tr>`
    );
  }

  function escHtml(str) {
    return String(str ?? '')
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

});
