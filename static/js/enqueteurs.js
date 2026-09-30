/**
 * enqueteurs.js — Gestion des enquêteurs Solutions Terrain (v1.1, §7.2)
 * Source SQL (livrée par Philippe le 25/08) :
 *   - liste   : ft_Enqueteur_Terrain_Non_IFOP
 *   - création : Prc_Enqueteur_Terrain_Non_IFOP_Upsert
 *
 * La colonne "Voxco" (Voxco_User_Creation / Voxco_User_Date_Creation) est
 * modifiable depuis le 2026-09-29 : elle s'écrit via
 * Prc_Enqueteur_Terrain_Non_IFOP_Update_Voxco_Creation, livrée par Philippe le
 * 26/08 et restée inutilisée. Nicolas avait confirmé le 20/08 (§7.2.4 point 7)
 * qu'il fallait mémoriser l'état coché / décoché.
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
    // Tri alphabétique sur le nom (puis le prénom), insensible aux accents et à la casse.
    rows = rows.slice().sort(function (a, b) {
      return (a.Nom || '').localeCompare(b.Nom || '', 'fr', { sensitivity: 'base' })
          || (a.Prenom || '').localeCompare(b.Prenom || '', 'fr', { sensitivity: 'base' });
    });
    rows.forEach(function (r) {
      // Blocage IFOP : affiché seulement s'il est renseigné (géré par Philippe en base).
      const blocage = r.Date_Blocage_IFOP_Affectation
        ? `<span class="text-danger">${fmtDate(r.Date_Blocage_IFOP_Affectation)}${r.Motif_Blocage_IFOP_Affectation ? ' — ' + escHtml(r.Motif_Blocage_IFOP_Affectation) : ''}</span>`
        : '<span class="text-muted">—</span>';
      const titreVoxco = r.Voxco_User_Creation && r.Voxco_User_Date_Creation
        ? `Compte Voxco créé le ${fmtDate(r.Voxco_User_Date_Creation)}`
        : 'Compte Voxco';
      const voxco = `<input type="checkbox" class="form-check-input chk-voxco"
          data-id="${r.ID_Enqueteur_Terrain}" ${r.Voxco_User_Creation ? 'checked' : ''}
          title="${titreVoxco}">`;
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

  // ---- Case Voxco ----
  $(document).on('change', '.chk-voxco', function () {
    const $chk  = $(this);
    const actif = $chk.is(':checked');
    $chk.prop('disabled', true);

    ajaxPost('/api/enqueteurs-terrain/voxco/', {
      id_enqueteur: parseInt($chk.data('id')),
      actif:        actif,
    })
    .done(function (resp) {
      if (resp.status !== 'ok') {
        $chk.prop('checked', !actif);          // on remet l'état précédent
        alert(resp.message || 'Erreur lors de la mise à jour Voxco.');
      }
    })
    .fail(function (xhr) {
      $chk.prop('checked', !actif);
      const msg = xhr.responseJSON && xhr.responseJSON.message
        ? xhr.responseJSON.message
        : 'Erreur réseau lors de la mise à jour Voxco.';
      alert(msg);
    })
    .always(function () { $chk.prop('disabled', false); });
  });

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
