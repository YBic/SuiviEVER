/**
 * enqueteurs.js — Gestion des enquêteurs Solutions Terrain (v1.1, §7.2)
 * Source SQL (livrée par Philippe le 25/08) :
 *   - liste   : ft_Enqueteur_Terrain_Non_IFOP
 *   - création : Prc_Enqueteur_Terrain_Non_IFOP_Upsert
 *
 * La colonne "Voxco" est un statut réel (Voxco_User_Creation /
 * Voxco_User_Date_Creation), affiché en LECTURE SEULE : la procédure de
 * création n'a aucun paramètre pour l'écrire depuis l'appli — probablement
 * alimentée par une synchronisation externe (décision du 2026-08-25).
 */
$(function () {

  loadData();
  $('#btn-refresh-data').on('click', loadData);

  // ---- Création ----
  const modalCreation = new bootstrap.Modal('#modal-creation-enqueteur');

  $('#btn-creer-enqueteur').on('click', function () {
    $('#creation-enq-nom, #creation-enq-prenom').val('').removeClass('is-invalid');
    $('#creation-enq-error').addClass('d-none').text('');
    modalCreation.show();
  });

  $('#btn-valider-creation-enq').on('click', function () {
    const nom    = $('#creation-enq-nom').val().trim();
    const prenom = $('#creation-enq-prenom').val().trim();

    $('#creation-enq-nom, #creation-enq-prenom').removeClass('is-invalid');
    $('#creation-enq-error').addClass('d-none').text('');

    let manquant = false;
    if (!nom)    { $('#creation-enq-nom').addClass('is-invalid');    manquant = true; }
    if (!prenom) { $('#creation-enq-prenom').addClass('is-invalid'); manquant = true; }
    if (manquant) {
      showCreationError('Informations manquantes.');
      return;
    }

    showSpinner();
    ajaxPost('/api/enqueteurs-terrain/create/', { nom, prenom })
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
    $('#creation-enq-error').removeClass('d-none').text(msg);
  }

  // ---- Liste ----
  function loadData() {
    showSpinner();
    $.get('/api/enqueteurs-terrain/')
    .done(function (resp) {
      if (resp.status !== 'ok') { showError(resp.message); return; }
      renderTable(resp.data || []);
      markRefresh();
    })
    .fail(() => showError('Erreur réseau.'))
    .always(hideSpinner);
  }

  function renderTable(rows) {
    const $tbody = $('#tbody-enqueteurs').empty();
    if (!rows.length) {
      $tbody.append('<tr><td colspan="7" class="text-center text-muted py-4">Aucun enquêteur actif.</td></tr>');
      return;
    }
    rows.forEach(function (r) {
      // Blocage IFOP : affiché seulement s'il est renseigné (géré par Philippe en base).
      const blocage = r.Date_Blocage_IFOP_Affectation
        ? `<span class="text-danger">${fmtDate(r.Date_Blocage_IFOP_Affectation)}${r.Motif_Blocage_IFOP_Affectation ? ' — ' + escHtml(r.Motif_Blocage_IFOP_Affectation) : ''}</span>`
        : '<span class="text-muted">—</span>';
      const voxco = r.Voxco_User_Creation
        ? `<i class="bi bi-check-circle-fill text-success" title="Compte Voxco créé${r.Voxco_User_Date_Creation ? ' le ' + fmtDate(r.Voxco_User_Date_Creation) : ''}"></i>`
        : '<i class="bi bi-dash-circle text-muted" title="Compte Voxco non créé"></i>';
      $tbody.append(`<tr>
        <td class="cell-code">${escHtml(r.Matricule_Enqueteur_Terrain)}</td>
        <td>${escHtml(r.Nom)}</td>
        <td>${escHtml(r.Prenom)}</td>
        <td>${fmtDate(r.Date_Debut_Mission)}</td>
        <td>${r.Date_Fin_Mission ? fmtDate(r.Date_Fin_Mission) : '<span class="text-muted">—</span>'}</td>
        <td>${blocage}</td>
        <td class="text-center">${voxco}</td>
      </tr>`);
    });
  }

  function showError(msg) {
    $('#tbody-enqueteurs').html(
      `<tr><td colspan="7" class="text-center text-danger py-4">
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
