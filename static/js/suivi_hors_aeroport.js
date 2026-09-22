/**
 * suivi_hors_aeroport.js — Suivi des vacations hors aéroport (zones)
 * Source SQL : ft_EVER_Tableau_Zone_Chef_Equipe (liste) + ft_EVER_Tableau_Zone_Site_Chef_Equipe (détail).
 * Le tableau principal affiche une ligne par vacation zone (agrégée côté serveur) ;
 * le détail des sites est chargé au clic.
 */

$(function () {

  let lastRows = [];   // données brutes pour l'export CSV

  // ---- Persistance des filtres (sessionStorage) ----
  const FS = {
    save() {
      sessionStorage.setItem('ever.date',                   $('#filter-date').val());
      sessionStorage.setItem('ever.hors_aeroport.site',     $('#filter-site').val());
      sessionStorage.setItem('ever.hors_aeroport.enqueteur', $('#filter-enqueteur').val());
    },
    restore() {
      const date = sessionStorage.getItem('ever.date');
      setFilterDate(date);
    },
  };
  FS.restore();

  loadSites();
  if (CAN_FILTER_ENQUETEUR) loadEnqueteurs();
  loadData();
  window.everReloadData = loadData;   // rechargement après sauvegarde d'un commentaire

  $('#filter-date, #filter-site, #filter-enqueteur').on('change', function () {
    FS.save();
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
      const prev = $sel.val() || sessionStorage.getItem('ever.hors_aeroport.site');
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
      const prev = $sel.val() || sessionStorage.getItem('ever.hors_aeroport.enqueteur');
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
      if (resp.status !== 'ok') {
        showError(resp.message);
        lastRows = [];
        $('#btn-export-csv').prop('disabled', true);
        return;
      }
      lastRows = resp.data || [];
      $('#btn-export-csv').prop('disabled', lastRows.length === 0);
      renderTable(lastRows);
      markRefresh();
    })
    .fail(() => { showError('Erreur réseau.'); lastRows = []; $('#btn-export-csv').prop('disabled', true); })
    .always(hideSpinner);
  }

  function renderTable(rows) {
    const $tbody = $('#tbody-hors-aeroport').empty();
    $('#panel-detail-vacation').addClass('d-none');

    if (!rows || rows.length === 0) {
      $tbody.append('<tr><td colspan="10" class="text-center text-muted py-4">Aucune vacation pour ces critères.</td></tr>');
      return;
    }

    // Grouper par zone d'enquête
    const zones = {};
    rows.forEach(function (r) {
      const key = r.Nom_Zone || '?';
      if (!zones[key]) zones[key] = { nom: r.Nom_Zone, rows: [], totals: newTotals() };
      zones[key].rows.push(r);
      accumulate(zones[key].totals, r);
    });

    Object.values(zones).forEach(function (zone) {
      zone.rows.forEach(r => $tbody.append(buildVacationRow(r)));
      $tbody.append(buildTotalRow(zone.nom, zone.totals));
    });
  }

  function newTotals() {
    return { objectif: 0, hasObj: false, completes: 0, recrutes: 0, valides: 0 };
  }

  function accumulate(t, r) {
    if (r.Objectif != null) { t.objectif += toInt(r.Objectif); t.hasObj = true; }
    t.completes += toInt(r.Completes_100);
    t.recrutes  += toInt(r.Recrutes);
    t.valides   += toInt(r.Face_A_Face);
  }

  function toInt(v) { return parseInt(v) || 0; }

  function buildVacationRow(r) {
    const completes = toInt(r.Completes_100);
    const objectif  = r.Objectif != null ? toInt(r.Objectif) : null;   // null = zone sans objectif
    const isComplete = objectif > 0 && completes >= objectif;
    const taux = objectif > 0 ? Math.round((completes / objectif) * 100) : null;
    const tauxCls = taux != null ? rateClass(taux + '%') : '';

    const detailBtn = r.ID_Vacation
      ? `<button class="btn btn-sm btn-outline-secondary btn-detail"
           data-id="${r.ID_Vacation || ''}" data-num="${r.Numero_Vacation || ''}"
           title="Voir les sites"><i class="bi bi-list-ul"></i></button>`
      : '<span class="text-muted">—</span>';

    // Le bouton commentaire est désormais dans le détail des sites (pas ici).
    return `<tr class="row-vacation ${isComplete ? 'row-complete' : ''}">
      <td>${escHtml(r.Nom_Zone || '')}</td>
      <td class="cell-code">${escHtml(r.Numero_Vacation || '')}</td>
      <td title="${escHtml(r.Libelle_Enqueteur || '')}"><div class="cell-enqueteur">${escHtml(r.Libelle_Enqueteur || '')}</div></td>
      <td class="text-end">${objectif != null ? (objectif || '—') : '<span class="text-muted">N/A</span>'}</td>
      <td class="text-end">${completes}</td>
      <td class="cell-rate">${taux != null ? `<span class="rate-pill ${tauxCls}">${taux}%</span>` : '<span class="text-muted">—</span>'}</td>
      <td class="text-end">${toInt(r.Recrutes)}</td>
      <td class="text-end">${toInt(r.Face_A_Face)}</td>
      <td class="text-end">${Math.max(0, completes - toInt(r.Face_A_Face))}</td>
      <td class="text-center">${detailBtn}</td>
    </tr>`;
  }

  function buildTotalRow(nom, t) {
    const taux = t.hasObj && t.objectif > 0 ? Math.round((t.completes / t.objectif) * 100) : null;
    return `<tr class="row-total-site">
      <td colspan="3">TOTAL – ${escHtml(nom)}</td>
      <td class="text-end">${t.hasObj ? t.objectif : '—'}</td>
      <td class="text-end">${t.completes}</td>
      <td class="text-end">${taux != null ? taux + '%' : '—'}</td>
      <td class="text-end">${t.recrutes}</td>
      <td class="text-end">${t.valides}</td>
      <td class="text-end">${Math.max(0, t.completes - t.valides)}</td>
      <td></td>
    </tr>`;
  }

  // ---- Détail vacation multi-sites ----
  let currentDetail = null;   // { id, num } de la vacation zone affichée dans le détail

  function loadDetail(idVacation, num) {
    currentDetail = { id: idVacation, num: num };
    showSpinner();
    $.get('/api/suivi/hors-aeroport/detail/', { id_vacation: idVacation })
    .done(function (resp) {
      if (resp.status !== 'ok') { alert('Erreur chargement détail.'); return; }
      renderDetail(num, resp.data);
    })
    .fail(() => alert('Erreur réseau.'))
    .always(hideSpinner);
  }

  $(document).on('click', '.btn-detail', function () {
    loadDetail($(this).data('id'), $(this).data('num'));
  });

  // Rechargement du détail après sauvegarde d'un commentaire site (appelé par ever.js)
  window.everReloadDetail = function () {
    if (currentDetail) loadDetail(currentDetail.id, currentDetail.num);
  };

  function renderDetail(num, rows) {
    $('#detail-vacation-num').text(num);
    const $tbody = $('#tbody-detail-sites').empty();

    rows.forEach(function (r) {
      let trainInfo = '—';
      if (r.Nbre_Trains) {
        const horaires = (r.Heure_Train_Min && r.Heure_Train_Max)
          ? ` · ${escHtml(r.Heure_Train_Min)}→${escHtml(r.Heure_Train_Max)}`
          : '';
        const gares = r.Gares_Terminus
          ? `<br><small class="text-muted">${escHtml(r.Gares_Terminus)}</small>`
          : '';
        trainInfo = `${r.Nbre_Trains} train(s)${horaires}${gares}`;
      }
      const typeBadge = r.Sites_Autres
        ? '<span class="badge bg-light text-dark border">Autres sites</span>'
        : `<span class="badge bg-secondary">${escHtml(r.Type_Site || '')}</span>`;
      const objectif = r.Objectif_Total != null ? (toInt(r.Objectif_Total) || '—') : '<span class="text-muted">N/A</span>';

      // Bouton commentaire (mode zone) — sauf "Sites Autres" (non géré par la SP).
      // Le détail d'une vacation zone ne contient qu'un enquêteur : on n'édite
      // que son rang ; l'autre enquêteur (binôme = autre vacation zone) n'est
      // pas touché par cet écran.
      let cmntCell = '';
      if (CAN_COMMENT) {
        const rang = toInt(r.Rang_Enqueteur) || 1;
        const vac  = escHtml(r.Commentaire_Vacation || '');
        const site = escHtml(r.Commentaire_Site || '');
        const own  = r.Commentaire_Vacation || r.Commentaire_Site;
        const slots = rang === 2
          ? `data-vac1="" data-vol1="" data-vac2="${vac}" data-vol2="${site}"`
          : `data-vac1="${vac}" data-vol1="${site}" data-vac2="" data-vol2=""`;
        cmntCell = r.Sites_Autres
          ? '<td></td>'
          : `<td class="text-center"><button class="btn-comment ${own ? 'has-comment' : ''}"
               data-mode="zone"
               data-id="${r.ID_Vacation_Zone_Site || ''}"
               data-num="${escHtml(r.Nom_Site || '')}"
               data-rang="${rang}" ${slots}
               title="Commentaire"><i class="bi bi-chat-left-text"></i></button></td>`;
      }

      $tbody.append(`<tr>
        <td>${escHtml(r.Nom_Site || '')}</td>
        <td>${typeBadge}</td>
        <td>${escHtml(r.Libelle_Enqueteur || '')}</td>
        <td class="text-end">${objectif}</td>
        <td class="text-end">${toInt(r.Recrutes)}</td>
        <td class="text-end">${toInt(r.Valides)}</td>
        <td class="text-end">${toInt(r.FAF_Valides)}</td>
        <td class="text-end">${toInt(r.Abandons)}</td>
        <td>${trainInfo}</td>
        ${cmntCell}
      </tr>`);
    });
    $('#panel-detail-vacation').removeClass('d-none');
    $('html, body').animate({ scrollTop: $('#panel-detail-vacation').offset().top - 20 }, 300);
  }

  // ---- Export CSV ----
  $('#btn-export-csv').on('click', function () {
    if (!lastRows || lastRows.length === 0) return;

    const date = $('#filter-date').val() || 'export';

    const headers = [
      'Date', 'Zone', 'N° Vacation', 'Enquêteur',
      'Objectif', '100% complétés', 'Taux réal. (%)',
      'Recrutés', 'Face à Face', 'QR Code',
    ];

    const csvRows = [headers.join(';')];

    lastRows.forEach(function (r) {
      const objectif  = r.Objectif != null ? toInt(r.Objectif) : '';
      const completes = toInt(r.Completes_100);
      const faf       = toInt(r.Face_A_Face);
      const taux = objectif > 0 ? Math.round((completes / objectif) * 100) : '';

      const row = [
        date,
        r.Nom_Zone        || '',
        r.Numero_Vacation || '',
        r.Libelle_Enqueteur || '',
        objectif,
        completes,
        taux,
        toInt(r.Recrutes),
        faf,
        Math.max(0, completes - faf),
      ].map(function (v) {
        const s = String(v);
        return s.includes(';') || s.includes('"') || s.includes('\n')
          ? '"' + s.replace(/"/g, '""') + '"'
          : s;
      });

      csvRows.push(row.join(';'));
    });

    const bom  = '﻿';  // BOM UTF-8 pour Excel FR
    const blob = new Blob([bom + csvRows.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `suivi_zones_${date}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  });

  function showError(msg) {
    $('#tbody-hors-aeroport').html(
      `<tr><td colspan="10" class="text-center text-danger py-4">
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
