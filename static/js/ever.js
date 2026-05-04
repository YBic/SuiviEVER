/**
 * ever.js — JavaScript partagé (master page)
 * Horloge, spinner, commentaires, mot de passe affectation
 */

/* ---- Datepicker DD/MM/YYYY (Flatpickr) ---- */
if (document.getElementById('filter-date')) {
  flatpickr('#filter-date', {
    locale:      'fr',
    dateFormat:  'Y-m-d',    // valeur interne envoyée au serveur
    altInput:    true,
    altFormat:   'd/m/Y',    // affichage utilisateur
    allowInput:  true,
  });
}

/* ---- Horloge ---- */
function updateClock() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  $('#clock').text(
    `${pad(now.getDate())}/${pad(now.getMonth()+1)}/${now.getFullYear()} `+
    `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  );
}
setInterval(updateClock, 1000);
updateClock();

/* ---- Spinner ---- */
function showSpinner() { $('#loading-overlay').removeClass('d-none').css('display','flex'); }
function hideSpinner() { $('#loading-overlay').addClass('d-none'); }

/* ---- Rafraîchir (bouton header) ---- */
$('#btn-refresh').on('click', function () {
  $('#btn-refresh-data').trigger('click');
});

/* ---- CSRF token pour les requêtes POST ---- */
function getCsrfToken() {
  return $('[name=csrfmiddlewaretoken]').val() ||
         document.cookie.split('; ')
           .find(r => r.startsWith('csrftoken='))
           ?.split('=')[1] || '';
}

function ajaxPost(url, data) {
  return $.ajax({
    url,
    method: 'POST',
    contentType: 'application/json',
    headers: { 'X-CSRFToken': getCsrfToken() },
    data: JSON.stringify(data),
  });
}

/* ---- Colorisation taux ---- */
function rateClass(pct) {
  if (pct === null || pct === undefined || pct === '') return '';
  const val = parseFloat(String(pct).replace('%',''));
  if (isNaN(val)) return '';
  if (val >= 90) return 'good';
  if (val >= 60) return 'mid';
  return 'bad';
}

/* ---- Formatage d'un taux en % ---- */
function fmtRate(val, total) {
  if (!total || total === 0) return '—';
  return Math.round((val / total) * 100) + '%';
}

/* ---- Formatage date ISO → DD/MM/YYYY ---- */
function fmtDate(iso) {
  if (!iso || iso.length < 10) return iso || '';
  return iso.substring(8, 10) + '/' + iso.substring(5, 7) + '/' + iso.substring(0, 4);
}

/* ================================================================
   MODAL COMMENTAIRE
   ================================================================ */
const modalCommentaire = new bootstrap.Modal('#modal-commentaire');

$(document).on('click', '.btn-comment', function () {
  const $btn = $(this);
  $('#cmnt-id-vacation').val($btn.data('id'));
  $('#cmnt-vacation-num').text($btn.data('num') || '');
  $('#cmnt-avant').val($btn.data('avant') || '');
  $('#cmnt-apres').val($btn.data('apres') || '');
  modalCommentaire.show();
});

$('#btn-save-commentaire').on('click', function () {
  const idVacation = $('#cmnt-id-vacation').val();
  if (!idVacation) return;

  showSpinner();
  ajaxPost('/api/commentaire/', {
    id_vacation: parseInt(idVacation),
    commentaire_avant: $('#cmnt-avant').val() || null,
    commentaire_apres: $('#cmnt-apres').val() || null,
  })
  .done(function (resp) {
    if (resp.status === 'ok') {
      modalCommentaire.hide();
      // Mettre à jour le bouton dans le tableau
      const $btn = $(`.btn-comment[data-id="${idVacation}"]`);
      $btn.data('avant', $('#cmnt-avant').val());
      $btn.data('apres', $('#cmnt-apres').val());
      const hasComment = $('#cmnt-avant').val() || $('#cmnt-apres').val();
      $btn.toggleClass('has-comment', !!hasComment);
    }
  })
  .fail(function () {
    alert('Erreur lors de l\'enregistrement du commentaire.');
  })
  .always(hideSpinner);
});

/* ================================================================
   MODAL MOT DE PASSE AFFECTATION
   ================================================================ */
const modalPassword = new bootstrap.Modal('#modal-password');

function checkAffectationPassword(onSuccess) {
  $('#password-error').addClass('d-none');
  $('#affectation-password').val('');
  modalPassword.show();

  $('#btn-check-password').off('click').on('click', function () {
    const pwd = $('#affectation-password').val();
    showSpinner();
    ajaxPost('/api/affectation/password/', { password: pwd })
    .done(function (resp) {
      if (resp.status === 'ok') {
        modalPassword.hide();
        if (typeof onSuccess === 'function') onSuccess();
      }
    })
    .fail(function () {
      $('#password-error').removeClass('d-none');
    })
    .always(hideSpinner);
  });
}
