const API = "https://waltraud-unmalleable-fecklessly.ngrok-free.dev";

function headers() {
  return {
    "Content-Type": "application/json",
    Authorization: "Bearer " + localStorage.getItem("token"),
  };
}

function guard() {
  if (!localStorage.getItem("token")) {
    window.location.href = "/admin/login";
  }
}

function logout() {
  localStorage.removeItem("token");
  window.location.href = "/admin/login";
}
