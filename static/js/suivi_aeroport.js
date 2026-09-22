/**
 * suivi_aeroport.js — Suivi des vacations en aéroport
 */

$(function () {

  let lastRows = [];   // données brutes de la dernière réponse API (pour l'export)

  // ---- Persistance des filtres (sessionStorage) ----
  const FS = {
    save() {
      sessionStorage.setItem('ever.date',              $('#filter-date').val());
      sessionStorage.setItem('ever.aeroport.aeroport', $('#filter-aeroport').val());
      sessionStorage.setItem('ever.aeroport.enqueteur', $('#filter-enqueteur').val());
      sessionStorage.setItem('ever.aeroport.type_vol', $('#filter-type-vol').val());
    },
    restore() {
      const date = sessionStorage.getItem('ever.date');
      setFilterDate(date);
      // Les selects sont peuplés dynamiquement : on restaure après chargement via prev
    },
  };
  FS.restore();

  // ---- Chargement initial des listes ----
  loadAeroports();
  if (CAN_FILTER_ENQUETEUR) loadEnqueteurs();
  loadTypesVol();
  loadData();

  // ---- Événements filtres ----
  $('#filter-date, #filter-aeroport, #filter-enqueteur, #filter-type-vol').on('change', function () {
    FS.save();
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
      const prev = $sel.val() || sessionStorage.getItem('ever.aeroport.aeroport');
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
      const prev = $sel.val() || sessionStorage.getItem('ever.aeroport.enqueteur');
      $sel.find('option:not(:first)').remove();
      resp.data.forEach(function (e) {
        $sel.append(`<option value="${e.Id_Personne}">${e.Libelle_Enqueteur}</option>`);
      });
      if (prev) $sel.val(prev);
    });
  }

  // ---- Chargement types de vol (API) ----
  function loadTypesVol() {
    $.get('/api/types-vol/').done(function (resp) {
      if (resp.status !== 'ok') return;
      const $sel = $('#filter-type-vol');
      $sel.find('option:not(:first)').remove();
      resp.data.forEach(t => $sel.append(`<option value="${t.id}">${t.label}</option>`));
      const prev = sessionStorage.getItem('ever.aeroport.type_vol') || '1';
      if (prev) $sel.val(prev);
    });
  }

  // ---- Chargement & rendu des données ----
  function loadData() {
    showSpinner();
    const typeVol = $('#filter-type-vol').val() || '';
    // Cas "Autres Vols" (id=0) : la TVF SQL ne filtre pas sur ce type
    // (côté base les lignes Autres ont ID_Type_Vacation_Vol = NULL). On charge
    // donc "Tous" puis on filtre côté client sur le flag Vols_Autres.
    const isAutres = typeVol === '0';
    // Le filtre "Enquêteur" n'est PLUS transmis à l'API : il est appliqué
    // côté client dans renderTable(). Raison (bug remonté par Nicolas le
    // 2026-08-20) : quand un binôme partage un vol, filtrer côté serveur sur
    // un seul enquêteur fait disparaître la ligne de l'AUTRE enquêteur du
    // jeu de données reçu. Or le bouton commentaire doit porter les 2
    // commentaires du binôme pour ne pas écraser celui de l'enquêteur non
    // édité à la sauvegarde (la SP met à jour les 2 rangs en un seul appel).
    // Filtrer côté client garde toujours les 2 lignes disponibles pour cet
    // appariement, même si une seule est affichée.
    const params = {
      date:         $('#filter-date').val(),
      id_aeroport:  $('#filter-aeroport').val()  || '',
      id_type_vol:  isAutres ? '' : typeVol,
    };

    $.get('/api/suivi/aeroport/', params)
    .done(function (resp) {
      if (resp.status !== 'ok') {
        showError(resp.message || 'Erreur lors du chargement.');
        lastRows = [];
        $('#btn-export-csv').prop('disabled', true);
        return;
      }
      let data = resp.data || [];
      if (isAutres) data = data.filter(r => r.Vols_Autres);
      renderTable(data);   // renderTable met à jour lastRows (sous-ensemble affiché) et le bouton CSV
      markRefresh();
    })
    .fail(function () {
      showError('Erreur réseau.');
      lastRows = [];
      $('#btn-export-csv').prop('disabled', true);
    })
    .always(hideSpinner);
  }

  // Exposé pour ever.js : rechargement après sauvegarde d'un commentaire
  // (garantit que les boutons portent les valeurs à jour des 2 enquêteurs).
  window.everReloadData = loadData;

  // ---- Rendu du tableau hiérarchique ----
  // `rows` contient TOUTES les vacations reçues (jamais filtrées par enquêteur
  // côté serveur — voir loadData). Le filtre "Enquêteur" est appliqué ici,
  // côté client, mais l'appariement des commentaires du binôme (r1/r2) se
  // fait toujours sur la totalité des lignes d'un vol : sinon, l'enquêteur
  // masqué par le filtre verrait son commentaire effacé à la prochaine
  // sauvegarde (bug remonté par Nicolas le 2026-08-20).
  function renderTable(rows) {
    const $tbody = $('#tbody-aeroport').empty();
    const filterEnq = CAN_FILTER_ENQUETEUR ? ($('#filter-enqueteur').val() || '') : '';

    // Regroupement par vol : allRows = toutes les vacations du vol (pour
    // l'appariement des commentaires) ; displayRows = celles qui respectent
    // le filtre enquêteur (pour l'affichage et les totaux).
    const flights = {};   // { "code||vol": { code, nom, vol, allRows, displayRows, totals } }
    const codeOrder = [];

    rows.forEach(function (r) {
      const code = r.Code_Aeroport || '?';
      const nom  = r.Nom_Aeroport  || code;
      const vol  = r.Numero_Vol    || '—';
      const key  = code + '||' + vol;
      if (!flights[key]) {
        flights[key] = { code, nom, vol, allRows: [], displayRows: [], totals: newTotals() };
      }
      flights[key].allRows.push(r);
      if (!filterEnq || String(r.ID_Personne) === filterEnq) {
        flights[key].displayRows.push(r);
        accumulate(flights[key].totals, r);
      }
      if (!codeOrder.includes(code)) codeOrder.push(code);
    });

    const displayRows = Object.values(flights).flatMap(f => f.displayRows);
    lastRows = displayRows;
    $('#btn-export-csv').prop('disabled', displayRows.length === 0);

    if (!displayRows.length) {
      $tbody.append('<tr><td colspan="14" class="text-center text-muted py-4">Aucune vacation pour ces critères.</td></tr>');
      return;
    }

    codeOrder.forEach(function (code) {
      const flightsOfAirport = Object.values(flights).filter(f => f.code === code && f.displayRows.length > 0);
      if (!flightsOfAirport.length) return;

      const airportTotals = newTotals();
      const airportNom    = flightsOfAirport[0].nom;

      flightsOfAirport.forEach(function (f) {
        f.displayRows.forEach(r => accumulate(airportTotals, r));

        // Apparier les 2 enquêteurs du même vol à partir de TOUTES les lignes
        // du vol (f.allRows), pas seulement celles affichées : la SP de
        // commentaire met à jour les 2 enquêteurs en un seul appel, chaque
        // bouton doit donc porter les commentaires des deux rangs pour ne
        // jamais écraser celui de l'enquêteur masqué par le filtre.
        const r1 = f.allRows.find(x => (toInt(x.Rang_Enqueteur) || 1) === 1);
        const r2 = f.allRows.find(x => toInt(x.Rang_Enqueteur) === 2);
        const cmt = {
          vac1: r1 ? (r1.Commentaire_Vacation || '') : '',
          vol1: r1 ? (r1.Commentaire_Vol || '')      : '',
          vac2: r2 ? (r2.Commentaire_Vacation || '') : '',
          vol2: r2 ? (r2.Commentaire_Vol || '')      : '',
        };
        f.displayRows.forEach(function (r) {
          $tbody.append(buildVacationRow(r, cmt));
        });
        $tbody.append(buildTotalRow('row-total-vol', `Total vol <span class="cell-numvol">${escHtml(f.vol)}</span>`, f.totals));
      });
      $tbody.append(buildTotalRow('row-total-site', `TOTAL ${code} – ${escHtml(airportNom)}`, airportTotals));
    });
  }

  function newTotals() {
    // objectif      = somme tous types (pour les totaux vol)
    // objectifPrinc = somme vols principaux seulement (pour le total aéroport et le taux global)
    return { objectif: 0, objectifPrinc: 0, completes: 0, recrutes: 0, valides: 0 };
  }

  function accumulate(t, r) {
    t.objectif      += toInt(r.Objectif);
    if (r.ID_Type_Vacation_Vol === 1) t.objectifPrinc += toInt(r.Objectif);
    t.completes     += toInt(r.Completes_100);
    t.recrutes      += toInt(r.Recrutes);
    t.valides       += toInt(r.Face_A_Face);
  }

  function toInt(v) { return parseInt(v) || 0; }

  // ---- Badge type de vol ----
  // Vols Autres : ID_Type_Vacation_Vol est NULL côté SQL → on s'appuie sur le flag.
  function buildTypeBadge(idType, label, volsAutres) {
    if (volsAutres || idType === 0) {
      return `<span class="tvb tvb-a" title="${escHtml(label||'Autres vols')}"><i class="bi bi-three-dots"></i></span>`;
    }
    switch (idType) {
      case 1: return `<span class="tvb tvb-p" title="${escHtml(label||'Vol principal')}">P</span>`;
      case 2: return `<span class="tvb tvb-c" title="${escHtml(label||'Vol complémentaire')}">C</span>`;
      case 3: return `<span class="tvb tvb-o" title="${escHtml(label||'Vol optionnel')}">O</span>`;
      default: return escHtml(label || '');
    }
  }

  function buildVacationRow(r, cmt) {
    const completes  = toInt(r.Completes_100);
    const objectif   = r.Objectif != null ? toInt(r.Objectif) : null;   // null = Vols Autres
    const volsAutres = !!r.Vols_Autres;
    const isComplete = objectif > 0 && completes >= objectif;
    const taux       = objectif > 0 ? Math.round((completes / objectif) * 100) : null;
    const tauxCls    = taux != null ? rateClass(taux + '%') : '';

    const rang = toInt(r.Rang_Enqueteur) || 1;
    // cmt = commentaires des 2 enquêteurs du vol (appariés dans renderTable).
    // Le bouton porte les 4 valeurs ; le modal n'édite que le rang de la ligne.
    const c = cmt || { vac1: '', vol1: '', vac2: '', vol2: '' };
    const ownVac = rang === 2 ? c.vac2 : c.vac1;
    const ownVol = rang === 2 ? c.vol2 : c.vol1;
    // Pas de bouton commentaire pour les Vols Autres (SP non supportée)
    const cmntBtn = CAN_COMMENT && !volsAutres
      ? `<button class="btn-comment ${ownVac || ownVol ? 'has-comment' : ''}"
           data-id="${r.ID_Vacation_Vol || ''}"
           data-num="${r.Numero_Vacation || ''}"
           data-rang="${rang}"
           data-vac1="${escHtml(c.vac1)}" data-vol1="${escHtml(c.vol1)}"
           data-vac2="${escHtml(c.vac2)}" data-vol2="${escHtml(c.vol2)}"
           title="Commentaire"><i class="bi bi-chat-left-text"></i></button>`
      : '';

    return `<tr class="row-vacation ${isComplete ? 'row-complete' : ''} ${volsAutres ? 'row-vols-autres' : ''}">
      <td class="cell-aeroport text-center">${escHtml(r.Code_Aeroport || '')}</td>
      <td class="cell-code text-center">${escHtml(r.Numero_Vacation || '')}</td>
      <td title="${escHtml(r.Libelle_Enqueteur || '')}"><div class="cell-enqueteur">${escHtml(r.Libelle_Enqueteur || '')}</div></td>
      <td class="cell-numvol text-center" title="${escHtml((r.Nom_Compagnie ? r.Nom_Compagnie + ' · ' : '') + (r.Numero_Vol || ''))}">${escHtml(r.Numero_Vol || '')}</td>
      <td class="text-center">${buildTypeBadge(r.ID_Type_Vacation_Vol, r.Type_Vacation_Vol, volsAutres)}</td>
      <td title="${escHtml(r.Aeroport_Destination || '')}"><div class="cell-clip">${escHtml(r.Aeroport_Destination || '')}</div></td>
      <td class="text-center">${escHtml(r.Heure_Depart || '')}</td>
      <td class="text-end">${objectif != null ? (objectif || '—') : '<span class="text-muted">N/A</span>'}</td>
      <td class="text-end">${completes}</td>
      <td class="cell-rate">${taux != null ? `<span class="rate-pill ${tauxCls}">${taux}%</span>` : '<span class="text-muted">—</span>'}</td>
      <td class="text-end">${toInt(r.Recrutes)}</td>
      <td class="text-end">${toInt(r.Face_A_Face)}</td>
      <td class="text-end">${Math.max(0, completes - toInt(r.Face_A_Face))}</td>
      ${CAN_COMMENT ? `<td class="text-center">${cmntBtn}</td>` : ''}
    </tr>`;
  }

  function buildTotalRow(cls, label, t) {
    // Total aéroport : objectif et taux calculés sur les vols principaux uniquement
    const isSite  = cls === 'row-total-site';
    const objAff  = isSite ? t.objectifPrinc : t.objectif;
    const taux    = objAff > 0 ? Math.round((t.completes / objAff) * 100) : 0;
    const tauxCls = cls === 'row-total-vol' ? rateClass(taux + '%') : '';
    return `<tr class="${cls}">
      <td colspan="7">${label}</td>
      <td class="text-end">${objAff}</td>
      <td class="text-end">${t.completes}</td>
      <td class="text-end ${tauxCls}">${taux}%</td>
      <td class="text-end">${t.recrutes}</td>
      <td class="text-end">${t.valides}</td>
      <td class="text-end">${Math.max(0, t.completes - t.valides)}</td>
      ${CAN_COMMENT ? '<td></td>' : ''}
    </tr>`;
  }

  // ---- Export CSV ----
  $('#btn-export-csv').on('click', function () {
    if (!lastRows || lastRows.length === 0) return;

    const date = $('#filter-date').val() || 'export';

    const headers = [
      'Date', 'Aéroport', 'N° Vacation', 'Enquêteur',
      'N° Vol', 'Type vol', 'Compagnie', 'Destination', 'Heure départ',
      'Objectif', '100% complétés', 'Taux réal. (%)',
      'Recrutés', 'Face à Face', 'QR Code',
    ];

    const csvRows = [headers.join(';')];

    lastRows.forEach(function (r) {
      const objectif  = r.Objectif != null ? toInt(r.Objectif) : '';
      const completes = toInt(r.Completes_100);
      const taux = objectif > 0 ? Math.round((completes / objectif) * 100) : '';

      const row = [
        date,
        r.Code_Aeroport  || '',
        r.Numero_Vacation || '',
        r.Libelle_Enqueteur || '',
        r.Numero_Vol     || '',
        r.Type_Vacation_Vol || '',
        r.Nom_Compagnie  || '',
        r.Aeroport_Destination || '',
        r.Heure_Depart   || '',
        objectif,
        completes,
        taux,
        toInt(r.Recrutes),
        toInt(r.Face_A_Face),
        Math.max(0, completes - toInt(r.Face_A_Face)),
      ].map(function (v) {
        const s = String(v);
        return s.includes(';') || s.includes('"') || s.includes('\n')
          ? '"' + s.replace(/"/g, '""') + '"'
          : s;
      });

      csvRows.push(row.join(';'));
    });

    const bom  = '﻿';   // BOM UTF-8 pour Excel FR
    const blob = new Blob([bom + csvRows.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `suivi_aeroport_${date}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  });

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
