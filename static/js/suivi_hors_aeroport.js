/**
 * suivi_hors_aeroport.js — Suivi des vacations hors aéroport
 */

$(function () {

  loadSites();
  if (CAN_FILTER_ENQUETEUR) loadEnqueteurs();
  loadData();

  $('#filter-date, #filter-site, #filter-enqueteur').on('change', function () {
    loadSites();
    if (CAN_FILTER_ENQUETEUR) loadEnqueteurs();
    loadData();
  });
  $('#btn-refresh-data').on('click', loadData);
  $('#btn-close-detail').on('click', () => $('#panel-detail-vacation').addClass('d-none'));

  function loadSites() {
    const date = $('#filter-date').val();
    $.get('/api/sites/', { date })
    .done(function (resp) {
      if (resp.status !== 'ok') return;
      const $sel = $('#filter-site');
      const prev = $sel.val();
      $sel.find('option:not(:first)').remove();
      resp.data.forEach(function (s) {
        $sel.append(`<option value="${s.Id_Site}">[${s.Type_Site}] ${s.Nom_Site}</option>`);
      });
      if (prev) $sel.val(prev);
    });
  }

  function loadEnqueteurs() {
    const date = $('#filter-date').val();
    const id_site = $('#filter-site').val() || '';
    $.get('/api/enqueteurs/site/', { date, id_site })
    .done(function (resp) {
      if (resp.status !== 'ok') return;
      const $sel = $('#filter-enqueteur');
      const prev = $sel.val();
      $sel.find('option:not(:first)').remove();
      resp.data.forEach(e => $sel.append(`<option value="${e.Id_Personne}">${e.Libelle_Enqueteur}</option>`));
      if (prev) $sel.val(prev);
    });
  }

  function loadData() {
    showSpinner();
    const params = {
      date:        $('#filter-date').val(),
      id_site:     $('#filter-site').val()      || '',
      id_personne: CAN_FILTER_ENQUETEUR ? ($('#filter-enqueteur').val() || '') : '',
    };

    $.get('/api/suivi/hors-aeroport/', params)
    .done(function (resp) {
      if (resp.status !== 'ok') { showError(resp.message); return; }
      renderTable(resp.data);
    })
    .fail(() => showError('Erreur réseau.'))
    .always(hideSpinner);
  }

  function renderTable(rows) {
    const $tbody = $('#tbody-hors-aeroport').empty();
    $('#panel-detail-vacation').addClass('d-none');

    if (!rows || rows.length === 0) {
      $tbody.append('<tr><td colspan="13" class="text-center text-muted py-4">Aucune vacation pour ces critères.</td></tr>');
      return;
    }

    // Grouper par site
    const sites = {};
    rows.forEach(function (r) {
      const key = r.Id_Site || r.Nom_Site || '?';
      if (!sites[key]) sites[key] = { nom: r.Nom_Site, type: r.Type_Site, rows: [], totals: newTotals() };
      sites[key].rows.push(r);
      accumulate(sites[key].totals, r);
    });

    Object.values(sites).forEach(function (site) {
      site.rows.forEach(r => $tbody.append(buildVacationRow(r)));
      $tbody.append(buildTotalRow(site.nom, site.totals));
    });
  }

  function newTotals() {
    return { objectif: 0, completes: 0, recrutes: 0, valides: 0, abandons: 0 };
  }

  function accumulate(t, r) {
    t.objectif  += toInt(r.Objectif);
    t.completes += toInt(r['Complet\u00e9s_100'] ?? r.Completes_100);
    t.recrutes  += toInt(r.Recrutes);
    t.valides   += toInt(r.Questionnaires_Valides);
    t.abandons  += toInt(r.Abandons);
  }

  function toInt(v) { return parseInt(v) || 0; }

  function buildVacationRow(r) {
    const completes = toInt(r['Complet\u00e9s_100'] ?? r.Completes_100);
    const objectif  = toInt(r.Objectif);
    const isComplete = objectif > 0 && completes >= objectif;
    const taux = objectif > 0 ? Math.round((completes / objectif) * 100) : 0;
    const tauxCls = rateClass(taux + '%');
    const isMulti = (r.Type_Site || '').toUpperCase() === 'MULTI';

    const detailBtn = isMulti
      ? `<button class="btn btn-sm btn-outline-secondary btn-detail"
           data-id="${r.ID_Vacation || ''}" data-num="${r.Numero_Vacation || ''}"
           title="Voir les sites"><i class="bi bi-list-ul"></i></button>`
      : '<span class="text-muted">—</span>';

    const cmntBtn = CAN_COMMENT
      ? `<button class="btn-comment ${r.Commentaire_Vacation ? 'has-comment' : ''}"
           data-id="${r.ID_Vacation || ''}"
           data-num="${r.Numero_Vacation || ''}"
           data-avant="${escHtml(r.Commentaire_Vacation || '')}"
           data-apres=""
           title="Commentaire"><i class="bi bi-chat-left-text"></i></button>`
      : '';

    return `<tr class="row-vacation ${isComplete ? 'row-complete' : ''}">
      <td>${escHtml(r.Nom_Site || '')}</td>
      <td><span class="badge ${isMulti ? 'bg-info' : 'bg-secondary'}">${escHtml(r.Type_Site || '')}</span></td>
      <td class="cell-code">${escHtml(r.Numero_Vacation || '')}</td>
      <td>${escHtml(r.Libelle_Enqueteur || '')}</td>
      <td class="text-end">${objectif || '—'}</td>
      <td class="text-end">${completes}</td>
      <td class="text-end cell-rate ${tauxCls}">${taux}%</td>
      <td class="text-end">${toInt(r.Recrutes)}</td>
      <td class="text-end">${toInt(r.Questionnaires_Valides)}</td>
      <td class="text-end">${toInt(r.Abandons)}</td>
      <td class="text-end">${Math.max(0, objectif - completes)}</td>
      <td class="text-center">${detailBtn}</td>
      ${CAN_COMMENT ? `<td class="text-center">${cmntBtn}</td>` : ''}
    </tr>`;
  }

  function buildTotalRow(nom, t) {
    const taux = t.objectif > 0 ? Math.round((t.completes / t.objectif) * 100) : 0;
    return `<tr class="row-total-site">
      <td colspan="4">TOTAL – ${escHtml(nom)}</td>
      <td class="text-end">${t.objectif}</td>
      <td class="text-end">${t.completes}</td>
      <td class="text-end">${taux}%</td>
      <td class="text-end">${t.recrutes}</td>
      <td class="text-end">${t.valides}</td>
      <td class="text-end">${t.abandons}</td>
      <td class="text-end">${Math.max(0, t.objectif - t.completes)}</td>
      <td></td>
      ${CAN_COMMENT ? '<td></td>' : ''}
    </tr>`;
  }

  // ---- Détail vacation multi-sites ----
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
    const $tbody = $('#tbody-detail-sites').empty();
    rows.forEach(function (r) {
      $tbody.append(`<tr>
        <td>${escHtml(r.Nom_Site || '')}</td>
        <td>${escHtml(r.Type_Site || '')}</td>
        <td class="text-end">${toInt(r.Completes_100)}</td>
        <td class="text-end">${toInt(r.Recrutes)}</td>
        <td class="text-end">${toInt(r.Valides)}</td>
        <td class="text-end">${toInt(r.Abandons)}</td>
      </tr>`);
    });
    $('#panel-detail-vacation').removeClass('d-none');
    $('html, body').animate({ scrollTop: $('#panel-detail-vacation').offset().top - 20 }, 300);
  }

  function showError(msg) {
    $('#tbody-hors-aeroport').html(
      `<tr><td colspan="13" class="text-center text-danger py-4">
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
