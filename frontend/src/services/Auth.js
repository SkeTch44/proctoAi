export async function loginUser(credentials) {
<<<<<<< HEAD
  const response = await fetch("http://localhost:5000/api/login", {
=======
  const response = await fetch("http://127.0.0.1:5000/api/login", {
>>>>>>> rohan
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || "Login failed");
  }

  return data;
}


export async function registerUser(payload) {
<<<<<<< HEAD
  const response = await fetch("http://localhost:5000/api/register", {
=======
  const response = await fetch("http://127.0.0.1:5000/api/register", {
>>>>>>> rohan
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || "Registration failed");
  }

  return data;
}
