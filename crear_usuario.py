from werkzeug.security import generate_password_hash, check_password_hash

# 1. Crear el hash (esto es lo que guardas en tu base de datos)
password_plano = "123"
password_hash = generate_password_hash(password_plano)

print(f"Hash generado:\n{password_hash}")

# 2. Verificar la contraseña (esto haces en el Login)
# Intentamos con la correcta
es_correcta = check_password_hash(password_hash, "123")
print(f"¿Es correcta?: {es_correcta}")  # True
