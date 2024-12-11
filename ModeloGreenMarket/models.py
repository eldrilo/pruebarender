from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin, Group, Permission
from django.contrib.auth.hashers import make_password
from datetime import timedelta, timezone
from django.utils.timezone import now
import random

# Create your models here.

class Admin (BaseUserManager):
    def _create_user(self, username, correo_user, nom_user, ap_user, password, is_staff, is_superuser, rol, **extra_fields):
        user = self.model(
            username = username,
            correo_user = self.normalize_email(correo_user),
            nom_user = nom_user,
            ap_user = ap_user,
            is_staff = is_staff,
            is_superuser = is_superuser,
            rol = rol,
            **extra_fields
        )
        user.set_password(password)
        user.save(using = self.db)
        return user
    def create_superuser(self, username, correo_user, nom_user, ap_user, password=None, **extra_fields):
        return self._create_user(username, correo_user, nom_user, ap_user, password, True, True, "admin", **extra_fields)
    
    def create_usercli(self, username, correo_user, nom_user, ap_user, password=None, **extra_fields):
        return self._create_user(username, correo_user, nom_user, ap_user, password, False, False, "cliente", **extra_fields)
    
    def create_user_from_cart(self, rut, correo_user, nom_user, ap_user, **extra_fields):
        # Crear usuario cliente basado en el RUT o correo
        user = self.model(
            username = rut,
            correo_user = self.normalize_email(correo_user),
            nom_user = nom_user,
            ap_user = ap_user,
            is_staff = False,
            is_superuser = False,
            rol = "cliente",
            **extra_fields
        )
        # Autogenerar contraseña o dejar que sea sin contraseña
        user.set_unusable_password()  # Si no deseas que inicie sesión directamente
        user.save(using=self._db)
        return user

    def create_proveedor(self, rut, correo_user, nom_user, ap_user, password=None, **extra_fields):
        extra_fields.pop('username', None)
        extra_fields.pop('rol', None)
        proveedor = self.model(
            username = rut,  # Se usará el RUT como username
            correo_user = self.normalize_email(correo_user),
            nom_user = nom_user,
            ap_user = ap_user,
            is_staff = False,  # No es staff por defecto
            is_superuser = False,  # No es superuser
            rol = "proveedor",  # Asignar rol de proveedor
            **extra_fields
        )
        proveedor.set_password(password)
        proveedor.save(using=self._db)
        return proveedor

    def create_proveedor_admin(self, rut, correo_user, nom_user, ap_user, password=None, **extra_fields):
        # Este método lo usará el administrador para crear un proveedor
        return self.create_proveedor(rut, correo_user, nom_user, ap_user, password, **extra_fields)
    

# Opciones para los roles de usuarios
CHOICES_ROLES = [
    ('admin', 'Administrador'),
    ('cliente', 'Cliente'),
    ('proveedor', 'Proveedor')
]

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=30, unique=True)  # Seguir usando username para rut
    correo_user = models.EmailField("Correo", max_length=100, unique=True)
    rut = models.CharField("RUT", max_length=10, blank=True, null=True, unique=True)  # Campo opcional de RUT
    nom_user = models.CharField("Nombre", max_length=20, blank=True, null=True, default="(Sin Nombre)")
    ap_user = models.CharField("Apellido", max_length=20, blank=True, null=True, default="(Sin Apellido)")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    rol = models.CharField(max_length=30, choices=CHOICES_ROLES)
    
    # Añade related_name para evitar conflictos
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_groups',  # Evita el conflicto con 'auth.User.groups'
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',  # Evita el conflicto con 'auth.User.user_permissions'
        blank=True
    )

    objects = Admin()

    USERNAME_FIELD = 'username'  # Seguimos usando el campo 'username' para login (será el RUT o correo)
    REQUIRED_FIELDS = ['correo_user', 'nom_user', 'ap_user']

    def __str__(self) -> str:
        return self.username

class Proveedor(models.Model):
    rut = models.CharField(max_length=10, primary_key=True)
    dv = models.CharField(max_length=1)
    correo_electronico = models.EmailField(max_length=50)
    contrasena = models.CharField(max_length=200)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    verificacion = models.BooleanField(default=False)
    direccion = models.CharField(max_length=200, null=True, blank=True)
    foto = models.ImageField(upload_to='proveedor_images/', null=True, blank=True)  # Campo de imagen

    def save(self, *args, **kwargs):
        # Codificar la contraseña si no está codificada aún
        if not self.contrasena.startswith('pbkdf2_'):
            self.contrasena = make_password(self.contrasena)

        # Eliminar la imagen anterior si se está subiendo una nueva
        if self.pk:
            old_instance = Proveedor.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.foto != self.foto:
                if old_instance.foto and old_instance.foto.path:
                    old_instance.foto.delete(save=False)
                    
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre} {self.apellido} (RUT: {self.rut})'
    
    def registrar_producto(self, nombre_producto, precio, imagen, categoria):
        # Método para registrar un nuevo producto
        nuevo_producto = Producto(
            nombre_producto=nombre_producto,
            precio=precio,
            imagen_producto=imagen,
            id_categoria=categoria,
            id_proveedor=self  # Asigna este proveedor al producto
        )
        nuevo_producto.save()
        return nuevo_producto
    

class TwoFactor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    def is_valid(self):
        return now() < self.created_at + timedelta(minutes=10)
    def generate_code(self):
        self.code = f"{random.randint(100000, 999999)}"
        self.save()

class PasswordReset(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    creado = models.DateTimeField(auto_now_add=True)
    def is_valid(self):
        expiration_time = self.creado + timedelta(hours=24)
        return now() < expiration_time

class Cliente(models.Model):
    rut = models.CharField(max_length=10, primary_key=True)
    dv = models.CharField(max_length=1, null=True)
    correo_electronico = models.EmailField(max_length=50, null=True)
    contrasena = models.CharField(max_length=200)
    nombre = models.CharField(max_length=50, null=True)
    direccion = models.CharField(max_length=50, null=True)

    def save(self, *args, **kwargs):
        # Codificar la contraseña si no está codificada aún
        if not self.contrasena.startswith('pbkdf2_'):
            self.contrasena = make_password(self.contrasena)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre} (RUT: {self.rut})'

class CalificacionProveedor(models.Model):
    id_calificacionProve = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name="calificaciones_proveedor")  # Cliente que realiza la calificación
    id_proveedor = models.OneToOneField(Proveedor, on_delete=models.CASCADE, related_name="calificacion")
    puntuacion = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comentario = models.TextField(blank=True)

    def __str__(self):
        return f'{self.proveedor} - Calificación: {self.puntuacion}'
    
class Categoria (models.Model):
    id_categoria = models.AutoField(primary_key= True)
    nombre_categoria = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre_categoria

class Producto (models.Model):
    codigo_producto = models.AutoField(primary_key=True)
    nombre_producto = models.CharField(max_length=50)
    precio = models.IntegerField()
    imagen_producto = models.ImageField(upload_to='producto_images/', null=True, blank=True)
    descripcion = models.CharField(max_length=300)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre_producto
    
class CalificacionProducto(models.Model):
    id_calificacionProduc = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name="calificaciones_productos")  # Cliente que realiza la calificación
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="calificaciones")
    puntuacion = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])  # Calificación entre 1 y 5
    comentario = models.TextField(blank=True)

    def __str__(self):
        return f'Calificación de {self.producto}: {self.puntuacion}'

# class MetodoPago (models.Model):
#     id_metodo_pago = models.AutoField(primary_key=True)
#     nombre_metodo = models.CharField(max_length=50)

# class transaccion (models.Model):
#     id_transaccion = models.AutoField(primary_key=True)
#     monto = models.IntegerField()
#     fecha = models.DateField()
#     id_metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.CASCADE)
class transaccion(models.Model):
    metodo_pago = models.CharField(max_length=2)  # Ahora es un campo CharField para almacenar códigos como 'VD', 'VN'
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    buy_order = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    session_id = models.CharField(max_length=50)
    transaction_date = models.DateTimeField()

class Orden(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    items = models.JSONField()  # Guarda los productos y cantidades en formato JSON
    total = models.DecimalField(max_digits=10, decimal_places=2)
    pagado = models.BooleanField(default=False)
    buy_order = models.CharField(max_length=150)
    orden_date = models.DateTimeField(auto_now_add=True, blank=True)
    def __str__(self):
        return f"Orden {self.id} - Cliente {self.cliente.nombre}"

class CarritoM(models.Model):
    # Carrito asociado a un usuario, puede ser opcional si el carrito no está vinculado a usuarios autenticados
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Agrega este campo
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.cliente.nombre if self.cliente else 'Cliente Anónimo'} - {self.creado_en}"

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(CarritoM, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio = models.DecimalField(max_digits=10, decimal_places=2)  # Se almacena el precio al momento de la compra

    def subtotal(self):
        return self.precio * self.cantidad

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre_producto} en carrito {self.carrito.id}"

class Venta (models.Model):
    id_venta = models.AutoField(primary_key=True)
    fecha_venta = models.DateField()
    monto_total = models.IntegerField()
    id_cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    transaccion = models.ForeignKey(transaccion, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        # Validar que el carrito no esté asociado ya a otra venta
        if Venta.objects.filter(carrito=self.carrito).exists():
            raise ValueError("Este carrito ya está asociado a una venta.")
        super(Venta, self).save(*args, **kwargs)
