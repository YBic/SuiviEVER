/**
 * suivi_aeroport.js — Suivi des vacations en aéroport
 */

$(function () {

  // ---- Chargement initial des listes ----
  loadAeroports();
  if (CAN_FILTER_ENQUETEUR) loadEnqueteurs();
  loadTypesVol();
  loadData();

  // ---- Événements filtres ----
  $('#filter-date, #filter-aeroport, #filter-enqueteur, #filter-type-vol').on('change', function () {
    loadAeroports();
    if (CAN_FILTER_ENQUETEUR) loadEnqueteurs();
    loadData();
  });
  $('#btn-refresh-data').on('click', loadData);

  // ---- Chargement aéroports ----
  function loadAeroports() {
    const date = $('#filter-date').val();
    $.get('/api/aeroports/', { date })
    .done(function (resp) {
      if (resp.status !== 'ok') return;
      const $sel = $('#filter-aeroport');
      const prev = $sel.val();
      $sel.find('option:not(:first)').remove();
      resp.data.forEach(function (a) {
        $sel.append(`<option value="${a.Id_Aeroport}">${a.Code_Aeroport} – ${a.Nom_Aeroport}</option>`);
      });
      if (prev) $sel.val(prev);
    });
  }

  // ---- Chargement enquêteurs ----
  function loadEnqueteurs() {
    const date = $('#filter-date').val();
    const id_aeroport = $('#filter-aeroport').val() || '';
    $.get('/api/enqueteurs/aeroport/', { date, id_aeroport })
    .done(function (resp) {
      if (resp.status !== 'ok') return;
      const $sel = $('#filter-enqueteur');
      const prev = $sel.val();
      $sel.find('option:not(:first)').remove();
      resp.data.forEach(function (e) {
        $sel.append(`<option value="${e.Id_Personne}">${e.Libelle_Enqueteur}</option>`);
      });
      if (prev) $sel.val(prev);
    });
  }

  // ---- Chargement types de vol (statique pour l'instant) ----
  function loadTypesVol() {
    const types = [
      { id: 1, label: 'Principal' },
      { id: 2, label: 'Complémentaire' },
      { id: 3, label: 'Autre' },
    ];
    const $sel = $('#filter-type-vol');
    types.forEach(t => $sel.append(`<option value="${t.id}">${t.label}</option>`));
  }

  // ---- Chargement & rendu des données ----
  function loadData() {
    showSpinner();
    const params = {
      date:         $('#filter-date').val(),
      id_aeroport:  $('#filter-aeroport').val()  || '',
      id_personne:  CAN_FILTER_ENQUETEUR ? ($('#filter-enqueteur').val() || '') : '',
      id_type_vol:  $('#filter-type-vol').val()  || '',
    };

    $.get('/api/suivi/aeroport/', params)
    .done(function (resp) {
      if (resp.status !== 'ok') {
        showError(resp.message || 'Erreur lors du chargement.');
        return;
      }
      renderTable(resp.data);
    })
    .fail(function () { showError('Erreur réseau.'); })
    .always(hideSpinner);
  }

  // ---- Rendu du tableau hiérarchique ----
  function renderTable(rows) {
    const $tbody = $('#tbody-aeroport').empty();

    if (!rows || rows.length === 0) {
      $tbody.append('<tr><td colspan="14" class="text-center text-muted py-4">Aucune vacation pour ces critères.</td></tr>');
      return;
    }

    // Agrégation hiérarchique : aéroport → vol → vacations
    const airports = {};   // { code: { nom, flights: { num: { rows: [], totals } }, totals } }

    rows.forEach(function (r) {
      const code = r.Code_Aeroport || '?';
      const nom  = r.Nom_Aeroport  || code;
      const vol  = r.Numero_Vol    || '—';

      if (!airports[code]) airports[code] = { nom, flights: {}, totals: newTotals() };
      if (!airports[code].flights[vol]) airports[code].flights[vol] = { rows: [], totals: newTotals() };

      airports[code].flights[vol].rows.push(r);
      accumulate(airports[code].flights[vol].totals, r);
      accumulate(airports[code].totals, r);
    });

    // Rendu
    Object.entries(airports).forEach(function ([code, airport]) {
      Object.entries(airport.flights).forEach(function ([vol, flight]) {
        // Lignes vacation
        flight.rows.forEach(function (r, i) {
          $tbody.append(buildVacationRow(r));
        });
        // Total vol
        $tbody.append(buildTotalRow('row-total-vol', `Total vol ${vol}`, flight.totals));
      });
      // Total aéroport
      $tbody.append(buildTotalRow('row-total-site', `TOTAL ${code} – ${airport.nom}`, airport.totals));
    });
  }

  function newTotals() {
    return { objectif: 0, completes: 0, recrutes: 0, valides: 0, abandons: 0 };
  }

  function accumulate(t, r) {
    t.objectif  += toInt(r.Objectif);
    t.completes += toInt(r['Complet\u00e9s_100'] ?? r.Completes_100 ?? r['100%_compl\u00e9t\u00e9s']);
    t.recrutes  += toInt(r.Recrutes);
    t.valides   += toInt(r.Questionnaires_Valides);
    t.abandons  += toInt(r.Abandons);
  }

  function toInt(v) { return parseInt(v) || 0; }

  function buildVacationRow(r) {
    const completes = toInt(r['Complet\u00e9s_100'] ?? r.Completes_100 ?? r['100%_compl\u00e9t\u00e9s']);
    const objectif  = toInt(r.Objectif);
    const isComplete = objectif > 0 && completes >= objectif;
    const taux = objectif > 0 ? Math.round((completes / objectif) * 100) : 0;
    const tauxCls = rateClass(taux + '%');

    const cmntBtn = CAN_COMMENT
      ? `<button class="btn-comment ${r.Commentaire_Vacation || r.Commentaire_Vol ? 'has-comment' : ''}"
           data-id="${r.ID_Vacation_Vol || ''}"
           data-num="${r.Numero_Vacation || ''}"
           data-avant="${escHtml(r.Commentaire_Vacation || '')}"
           data-apres="${escHtml(r.Commentaire_Vol || '')}"
           title="Commentaire"><i class="bi bi-chat-left-text"></i></button>`
      : '';

    return `<tr class="row-vacation ${isComplete ? 'row-complete' : ''}">
      <td>${escHtml(r.Code_Aeroport || '')}</td>
      <td class="cell-code">${escHtml(r.Numero_Vacation || '')}</td>
      <td>${escHtml(r.Libelle_Enqueteur || '')}</td>
      <td>${escHtml(r.Code_Compagnie || '')} ${escHtml(r.Numero_Vol || '')}</td>
      <td>${escHtml(r.Aeroport_Destination || '')}</td>
      <td>${escHtml(r.Heure_Depart || '')}</td>
      <td class="text-end">${objectif || '—'}</td>
      <td class="text-end">${completes}</td>
      <td class="text-end cell-rate ${tauxCls}">${taux}%</td>
      <td class="text-end">${toInt(r.Recrutes)}</td>
      <td class="text-end">${toInt(r.Questionnaires_Valides)}</td>
      <td class="text-end">${toInt(r.Abandons)}</td>
      <td class="text-end">${Math.max(0, objectif - completes)}</td>
      ${CAN_COMMENT ? `<td class="text-center">${cmntBtn}</td>` : ''}
    </tr>`;
  }

  function buildTotalRow(cls, label, t) {
    const taux = t.objectif > 0 ? Math.round((t.completes / t.objectif) * 100) : 0;
    const tauxCls = cls === 'row-total-vol' ? rateClass(taux + '%') : '';
    return `<tr class="${cls}">
      <td colspan="6">${label}</td>
      <td class="text-end">${t.objectif}</td>
      <td class="text-end">${t.completes}</td>
      <td class="text-end ${tauxCls}">${taux}%</td>
      <td class="text-end">${t.recrutes}</td>
      <td class="text-end">${t.valides}</td>
      <td class="text-end">${t.abandons}</td>
      <td class="text-end">${Math.max(0, t.objectif - t.completes)}</td>
      ${CAN_COMMENT ? '<td></td>' : ''}
    </tr>`;
  }

  function showError(msg) {
    $('#tbody-aeroport').html(
      `<tr><td colspan="14" class="text-center text-danger py-4">
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
