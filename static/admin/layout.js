const API = "http://localhost:8000";

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
