print(">>> Bot arrancando...")
import os
import discord
from discord import app_commands
from discord.ext import commands
import db
from views import ConfirmView, StorePaginatorView, TasksPaginatorView, PendingSubmissionsPaginatorView

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def check_blocked(user_id: int) -> bool:
    return not db.is_blocked(user_id)

def admin_only(user_id: int) -> bool:
    return db.is_admin(user_id)

def ensure_player_registered(user_id: int, username: str):
    db.ensure_player(user_id, username)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos")
    except Exception as e:
        print(f"Error sincronizando comandos: {e}")

@bot.tree.command(name="ayuda", description="Muestra todos los comandos disponibles")
async def ayuda(interaction: discord.Interaction):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎄 Ayuda - Bot de Belén Colaborativo",
        description="Construye un Belén junto con otros usuarios.",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="💰 Comandos Generales",
        value="`/ayuda` - Muestra esta ayuda\n`/monedas` - Ver tu saldo",
        inline=False
    )
    
    embed.add_field(
        name="🏠 Sistema de Belén",
        value="`/crear_belen` - Crea tu propio belén\n`/unirse_belen` - Solicita unirte a un belén\n`/aceptar_solicitud` - Acepta una solicitud\n`/rechazar_solicitud` - Rechaza una solicitud\n`/salir_belen` - Sal de tu belén\n`/ver_belen` - Ver piezas y miembros",
        inline=False
    )
    
    embed.add_field(
        name="🏪 Tienda",
        value="`/tienda` - Ver catálogo de piezas\n`/tienda_comprar` - Comprar una pieza",
        inline=False
    )
    
    embed.add_field(
        name="📋 Tareas",
        value="`/tareas` - Ver tareas disponibles\n`/agregar_tarea` - Enviar tarea completada",
        inline=False
    )
    
    if db.is_admin(interaction.user.id):
        embed.add_field(
            name="⚙️ Comandos de Admin",
            value="**Usuarios:** `/agregar_admin`, `/admin_bloquear`, `/admin_desbloquear`, `/admin_dar_monedas`, `/admin_quitar_monedas`\n**Belenes:** `/admin_eliminar_belen`\n**Tienda:** `/admin_agregar_producto`, `/admin_modificar_producto`, `/admin_eliminar_producto`\n**Tareas:** `/admin_agregar_tarea`, `/admin_modificar_tarea`, `/admin_eliminar_tarea`, `/admin_aceptar_tarea`, `/admin_rechazar_tarea`, `/admin_ver_solicitudes_tareas`",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="monedas", description="Muestra tu saldo de monedas")
async def monedas(interaction: discord.Interaction):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    saldo = db.get_monedas(interaction.user.id)
    embed = discord.Embed(
        title="💰 Tu Saldo",
        description=f"Tienes **{saldo}** 🪙 monedas",
        color=discord.Color.gold()
    )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="crear_belen", description="Crea tu propio belén")
@app_commands.describe(nombre="Nombre del belén", descripcion="Descripción opcional del belén")
async def crear_belen(interaction: discord.Interaction, nombre: str, descripcion: str = None):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    existing = db.get_user_belen(interaction.user.id)
    if existing:
        await interaction.followup.send(f"Ya perteneces al belén **{existing['nombre']}**. Debes salir primero.", ephemeral=True)
        return
    
    existing_name = db.find_belen(nombre)
    if existing_name:
        await interaction.followup.send(f"Ya existe un belén con el nombre **{nombre}**.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏠 Crear Belén",
        description=f"¿Deseas crear el belén **{nombre}**?",
        color=discord.Color.blue()
    )
    if descripcion:
        embed.add_field(name="Descripción", value=descripcion, inline=False)
    
    async def on_confirm(inter: discord.Interaction):
        await inter.response.defer()
        belen_id = db.create_belen(nombre, interaction.user.id, descripcion)
        await inter.edit_original_response(
            content=f"✅ Belén **{nombre}** creado con éxito (ID: {belen_id}). ¡Ya eres miembro!",
            embed=None,
            view=None
        )
    
    async def on_cancel(inter: discord.Interaction):
        await inter.response.edit_message(content="Acción cancelada.", embed=None, view=None)
    
    view = ConfirmView(interaction.user.id, on_confirm, on_cancel)
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="unirse_belen", description="Solicita unirte a un belén")
@app_commands.describe(identificador="ID o nombre del belén")
async def unirse_belen(interaction: discord.Interaction, identificador: str):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    existing = db.get_user_belen(interaction.user.id)
    if existing:
        await interaction.followup.send(f"Ya perteneces al belén **{existing['nombre']}**. Debes salir primero.", ephemeral=True)
        return
    
    belen = db.find_belen(identificador)
    if not belen:
        await interaction.followup.send("No se encontró ese belén.", ephemeral=True)
        return
    
    request_id = db.create_join_request(belen['id'], interaction.user.id)
    
    try:
        creator = await bot.fetch_user(belen['creador_id'])
        embed = discord.Embed(
            title="📨 Nueva solicitud de unión",
            description=f"**{interaction.user.display_name}** quiere unirse a tu belén **{belen['nombre']}**.\n\nUsa `/aceptar_solicitud {request_id}` para aceptar o `/rechazar_solicitud {request_id}` para rechazar.",
            color=discord.Color.blue()
        )
        await creator.send(embed=embed)
        await interaction.followup.send(f"✅ Solicitud enviada al creador del belén **{belen['nombre']}** (ID solicitud: {request_id}).")
    except:
        await interaction.followup.send(f"✅ Solicitud creada (ID: {request_id}), pero no se pudo notificar al creador. Dile manualmente que revise las solicitudes.")

@bot.tree.command(name="aceptar_solicitud", description="Acepta una solicitud de unión a tu belén")
@app_commands.describe(solicitud_id="ID de la solicitud")
async def aceptar_solicitud(interaction: discord.Interaction, solicitud_id: int):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    request = db.get_join_request(solicitud_id)
    if not request:
        await interaction.followup.send("Solicitud no encontrada.", ephemeral=True)
        return
    
    if request['estado'] != 'pendiente':
        await interaction.followup.send("Esta solicitud ya fue procesada.", ephemeral=True)
        return
    
    if request['creador_id'] != interaction.user.id and not db.is_admin(interaction.user.id):
        await interaction.followup.send("No tienes permiso para gestionar esta solicitud.", ephemeral=True)
        return
    
    if db.accept_join_request(solicitud_id):
        await interaction.followup.send(f"✅ **{request['username']}** ha sido aceptado en el belén **{request['belen_nombre']}**.")
        try:
            user = await bot.fetch_user(request['jugador_id'])
            await user.send(f"🎉 Tu solicitud para unirte al belén **{request['belen_nombre']}** ha sido aceptada.")
        except:
            pass
    else:
        await interaction.followup.send("Error al procesar la solicitud.", ephemeral=True)

@bot.tree.command(name="rechazar_solicitud", description="Rechaza una solicitud de unión")
@app_commands.describe(solicitud_id="ID de la solicitud")
async def rechazar_solicitud(interaction: discord.Interaction, solicitud_id: int):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    request = db.get_join_request(solicitud_id)
    if not request:
        await interaction.followup.send("Solicitud no encontrada.", ephemeral=True)
        return
    
    if request['estado'] != 'pendiente':
        await interaction.followup.send("Esta solicitud ya fue procesada.", ephemeral=True)
        return
    
    if request['creador_id'] != interaction.user.id and not db.is_admin(interaction.user.id):
        await interaction.followup.send("No tienes permiso para gestionar esta solicitud.", ephemeral=True)
        return
    
    if db.reject_join_request(solicitud_id):
        await interaction.followup.send(f"❌ Solicitud de **{request['username']}** rechazada.")
        try:
            user = await bot.fetch_user(request['jugador_id'])
            await user.send(f"😔 Tu solicitud para unirte al belén **{request['belen_nombre']}** ha sido rechazada.")
        except:
            pass
    else:
        await interaction.followup.send("Error al procesar la solicitud.", ephemeral=True)

@bot.tree.command(name="salir_belen", description="Sal de tu belén actual")
async def salir_belen(interaction: discord.Interaction):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    belen = db.get_user_belen(interaction.user.id)
    if not belen:
        await interaction.followup.send("No perteneces a ningún belén.", ephemeral=True)
        return
    
    is_creator = belen['creador_id'] == interaction.user.id
    
    if is_creator:
        embed = discord.Embed(
            title="⚠️ Eliminar Belén",
            description=f"Eres el creador del belén **{belen['nombre']}**. Si sales, el belén será eliminado completamente. ¿Estás seguro?",
            color=discord.Color.red()
        )
    else:
        embed = discord.Embed(
            title="🚪 Salir del Belén",
            description=f"¿Deseas salir del belén **{belen['nombre']}**?",
            color=discord.Color.orange()
        )
    
    async def on_confirm(inter: discord.Interaction):
        await inter.response.defer()
        result = db.leave_belen(interaction.user.id)
        if result:
            if result['deleted']:
                await inter.edit_original_response(content=f"🗑️ El belén **{belen['nombre']}** ha sido eliminado.", embed=None, view=None)
            else:
                await inter.edit_original_response(content=f"👋 Has salido del belén **{belen['nombre']}**.", embed=None, view=None)
        else:
            await inter.edit_original_response(content="Error al procesar la salida.", embed=None, view=None)
    
    async def on_cancel(inter: discord.Interaction):
        await inter.response.edit_message(content="Acción cancelada.", embed=None, view=None)
    
    view = ConfirmView(interaction.user.id, on_confirm, on_cancel)
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="ver_belen", description="Ver información de tu belén")
async def ver_belen(interaction: discord.Interaction):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    belen = db.get_user_belen(interaction.user.id)
    if not belen:
        await interaction.followup.send("No perteneces a ningún belén.", ephemeral=True)
        return
    
    pieces = db.get_belen_pieces(belen['id'])
    members = db.get_belen_members(belen['id'])
    pending_requests = db.get_pending_requests_for_belen(belen['id'])
    
    embed = discord.Embed(
        title=f"🏠 Belén: {belen['nombre']} (ID: {belen['id']})",
        description=belen.get('descripcion') or "Sin descripción",
        color=discord.Color.green()
    )
    
    if pieces:
        pieces_text = "\n".join([f"{p['emoji']} {p['nombre']} x{p['cantidad']} (por {p['comprador']})" for p in pieces[:10]])
        if len(pieces) > 10:
            pieces_text += f"\n... y {len(pieces) - 10} más"
        embed.add_field(name="🎁 Piezas Compradas", value=pieces_text, inline=False)
    else:
        embed.add_field(name="🎁 Piezas Compradas", value="Ninguna todavía", inline=False)
    
    if members:
        members_text = "\n".join([f"{'👑' if m['id'] == belen['creador_id'] else '👤'} {m['username']} - {m['contribucion']} 🪙 contribuidos" for m in members])
        embed.add_field(name="👥 Miembros", value=members_text, inline=False)
    
    if pending_requests and belen['creador_id'] == interaction.user.id:
        requests_text = "\n".join([f"📨 {r['username']} (ID: {r['id']})" for r in pending_requests[:5]])
        embed.add_field(name="📨 Solicitudes Pendientes", value=requests_text, inline=False)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="tienda", description="Ver el catálogo de piezas")
async def tienda(interaction: discord.Interaction):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    items = db.list_store_items()
    view = StorePaginatorView(items, interaction.user.id)
    await interaction.followup.send(embed=view.get_embed(), view=view)

@bot.tree.command(name="tienda_comprar", description="Compra una pieza para tu belén")
@app_commands.describe(
    pieza="ID o nombre de la pieza",
    cantidad="Cantidad a comprar",
    belen="ID o nombre del belén (opcional si solo perteneces a uno)"
)
async def tienda_comprar(interaction: discord.Interaction, pieza: str, cantidad: int = 1, belen: str = None):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    if cantidad < 1:
        await interaction.followup.send("La cantidad debe ser al menos 1.", ephemeral=True)
        return
    
    user_belen = db.get_user_belen(interaction.user.id)
    if not user_belen:
        await interaction.followup.send("Debes pertenecer a un belén para comprar piezas.", ephemeral=True)
        return
    
    target_belen = user_belen
    if belen:
        target_belen = db.find_belen(belen)
        if not target_belen:
            await interaction.followup.send("No se encontró ese belén.", ephemeral=True)
            return
        if target_belen['id'] != user_belen['id']:
            await interaction.followup.send("Solo puedes comprar piezas para tu propio belén.", ephemeral=True)
            return
    
    item = db.get_store_item(pieza)
    if not item:
        await interaction.followup.send("No se encontró esa pieza en la tienda.", ephemeral=True)
        return
    
    total_cost = item['precio'] * cantidad
    current_balance = db.get_monedas(interaction.user.id)
    
    if current_balance < total_cost:
        await interaction.followup.send(f"No tienes suficientes monedas. Necesitas {total_cost} 🪙 pero tienes {current_balance} 🪙.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🛒 Confirmar Compra",
        description=f"¿Deseas comprar **{cantidad}x {item['emoji']} {item['nombre']}** por **{total_cost} 🪙**?",
        color=discord.Color.gold()
    )
    embed.add_field(name="Saldo actual", value=f"{current_balance} 🪙", inline=True)
    embed.add_field(name="Saldo después", value=f"{current_balance - total_cost} 🪙", inline=True)
    
    async def on_confirm(inter: discord.Interaction):
        await inter.response.defer()
        new_balance = db.update_monedas(interaction.user.id, -total_cost)
        db.record_purchase(target_belen['id'], item['id'], interaction.user.id, cantidad)
        await inter.edit_original_response(
            content=f"✅ Compraste **{cantidad}x {item['emoji']} {item['nombre']}** para el belén **{target_belen['nombre']}**. Saldo restante: {new_balance} 🪙",
            embed=None,
            view=None
        )
    
    async def on_cancel(inter: discord.Interaction):
        await inter.response.edit_message(content="Compra cancelada.", embed=None, view=None)
    
    view = ConfirmView(interaction.user.id, on_confirm, on_cancel)
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="tareas", description="Ver tareas disponibles")
async def tareas(interaction: discord.Interaction):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    tasks = db.get_available_tareas(interaction.user.id)
    view = TasksPaginatorView(tasks, interaction.user.id)
    await interaction.followup.send(embed=view.get_embed(), view=view)

@bot.tree.command(name="agregar_tarea", description="Envía una tarea completada para revisión")
@app_commands.describe(tarea_id="ID de la tarea", nota="Nota o evidencia opcional")
async def agregar_tarea(interaction: discord.Interaction, tarea_id: int, nota: str = None):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not check_blocked(interaction.user.id):
        await interaction.followup.send("Estás bloqueado y no puedes usar comandos.", ephemeral=True)
        return
    
    tarea = db.get_tarea(tarea_id)
    if not tarea:
        await interaction.followup.send("No se encontró esa tarea.", ephemeral=True)
        return
    
    if db.has_pending_submission(tarea_id, interaction.user.id):
        await interaction.followup.send("Ya tienes una solicitud pendiente para esta tarea.", ephemeral=True)
        return
    
    submission_id = db.submit_tarea(tarea_id, interaction.user.id, nota)
    await interaction.followup.send(f"✅ Solicitud de tarea **{tarea['nombre']}** enviada para revisión (ID: {submission_id}). Un administrador la revisará pronto.")

@bot.tree.command(name="agregar_admin", description="[ADMIN] Añade un administrador")
@app_commands.describe(usuario="Usuario a hacer admin")
async def agregar_admin(interaction: discord.Interaction, usuario: discord.User):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    db.ensure_player(usuario.id, usuario.display_name)
    if db.add_admin(usuario.id):
        await interaction.followup.send(f"✅ **{usuario.display_name}** ahora es administrador.")
    else:
        await interaction.followup.send(f"**{usuario.display_name}** ya es administrador.", ephemeral=True)

@bot.tree.command(name="admin_bloquear", description="[ADMIN] Bloquea a un usuario")
@app_commands.describe(usuario="Usuario a bloquear", razon="Razón del bloqueo")
async def admin_bloquear(interaction: discord.Interaction, usuario: discord.User, razon: str = None):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    db.ensure_player(usuario.id, usuario.display_name)
    if db.block_user(usuario.id, razon):
        await interaction.followup.send(f"🚫 **{usuario.display_name}** ha sido bloqueado.")
    else:
        await interaction.followup.send(f"**{usuario.display_name}** ya estaba bloqueado.", ephemeral=True)

@bot.tree.command(name="admin_desbloquear", description="[ADMIN] Desbloquea a un usuario")
@app_commands.describe(usuario="Usuario a desbloquear")
async def admin_desbloquear(interaction: discord.Interaction, usuario: discord.User):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    if db.unblock_user(usuario.id):
        await interaction.followup.send(f"✅ **{usuario.display_name}** ha sido desbloqueado.")
    else:
        await interaction.followup.send(f"**{usuario.display_name}** no estaba bloqueado.", ephemeral=True)

@bot.tree.command(name="admin_dar_monedas", description="[ADMIN] Da monedas a un usuario")
@app_commands.describe(usuario="Usuario", cantidad="Cantidad de monedas")
async def admin_dar_monedas(interaction: discord.Interaction, usuario: discord.User, cantidad: int):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    if cantidad <= 0:
        await interaction.followup.send("La cantidad debe ser positiva.", ephemeral=True)
        return
    
    db.ensure_player(usuario.id, usuario.display_name)
    new_balance = db.update_monedas(usuario.id, cantidad)
    await interaction.followup.send(f"✅ Se han dado **{cantidad} 🪙** a **{usuario.display_name}**. Nuevo saldo: {new_balance} 🪙")

@bot.tree.command(name="admin_quitar_monedas", description="[ADMIN] Quita monedas a un usuario")
@app_commands.describe(usuario="Usuario", cantidad="Cantidad de monedas")
async def admin_quitar_monedas(interaction: discord.Interaction, usuario: discord.User, cantidad: int):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    if cantidad <= 0:
        await interaction.followup.send("La cantidad debe ser positiva.", ephemeral=True)
        return
    
    new_balance = db.update_monedas(usuario.id, -cantidad)
    await interaction.followup.send(f"✅ Se han quitado **{cantidad} 🪙** a **{usuario.display_name}**. Nuevo saldo: {new_balance} 🪙")

@bot.tree.command(name="admin_eliminar_belen", description="[ADMIN] Elimina un belén")
@app_commands.describe(identificador="ID o nombre del belén")
async def admin_eliminar_belen(interaction: discord.Interaction, identificador: str):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    belen = db.find_belen(identificador)
    if not belen:
        await interaction.followup.send("No se encontró ese belén.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="⚠️ Eliminar Belén",
        description=f"¿Estás seguro de eliminar el belén **{belen['nombre']}**? Esta acción no se puede deshacer.",
        color=discord.Color.red()
    )
    
    async def on_confirm(inter: discord.Interaction):
        await inter.response.defer()
        if db.delete_belen(belen['id']):
            await inter.edit_original_response(content=f"🗑️ Belén **{belen['nombre']}** eliminado.", embed=None, view=None)
        else:
            await inter.edit_original_response(content="Error al eliminar el belén.", embed=None, view=None)
    
    async def on_cancel(inter: discord.Interaction):
        await inter.response.edit_message(content="Acción cancelada.", embed=None, view=None)
    
    view = ConfirmView(interaction.user.id, on_confirm, on_cancel)
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="admin_agregar_producto", description="[ADMIN] Añade un producto a la tienda")
@app_commands.describe(nombre="Nombre del producto", precio="Precio en monedas", descripcion="Descripción", emoji="Emoji del producto")
async def admin_agregar_producto(interaction: discord.Interaction, nombre: str, precio: int, descripcion: str = None, emoji: str = "🎁"):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    if precio <= 0:
        await interaction.followup.send("El precio debe ser positivo.", ephemeral=True)
        return
    
    try:
        item_id = db.create_store_item(nombre, precio, descripcion, emoji)
        await interaction.followup.send(f"✅ Producto **{emoji} {nombre}** añadido a la tienda (ID: {item_id}).")
    except Exception as e:
        await interaction.followup.send(f"Error al crear el producto: {str(e)}", ephemeral=True)

@bot.tree.command(name="admin_modificar_producto", description="[ADMIN] Modifica un producto")
@app_commands.describe(identificador="ID o nombre del producto", nombre="Nuevo nombre", precio="Nuevo precio", descripcion="Nueva descripción", emoji="Nuevo emoji")
async def admin_modificar_producto(interaction: discord.Interaction, identificador: str, nombre: str = None, precio: int = None, descripcion: str = None, emoji: str = None):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    item = db.get_store_item(identificador)
    if not item:
        await interaction.followup.send("No se encontró ese producto.", ephemeral=True)
        return
    
    if precio is not None and precio <= 0:
        await interaction.followup.send("El precio debe ser positivo.", ephemeral=True)
        return
    
    if db.update_store_item(item['id'], nombre, precio, descripcion, emoji):
        await interaction.followup.send(f"✅ Producto **{item['nombre']}** modificado.")
    else:
        await interaction.followup.send("No se realizaron cambios.", ephemeral=True)

@bot.tree.command(name="admin_eliminar_producto", description="[ADMIN] Elimina un producto de la tienda")
@app_commands.describe(identificador="ID o nombre del producto")
async def admin_eliminar_producto(interaction: discord.Interaction, identificador: str):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    item = db.get_store_item(identificador)
    if not item:
        await interaction.followup.send("No se encontró ese producto.", ephemeral=True)
        return
    
    if db.delete_store_item(item['id']):
        await interaction.followup.send(f"🗑️ Producto **{item['nombre']}** eliminado de la tienda.")
    else:
        await interaction.followup.send("Error al eliminar el producto.", ephemeral=True)

@bot.tree.command(name="admin_agregar_tarea", description="[ADMIN] Añade una tarea")
@app_commands.describe(nombre="Nombre de la tarea", descripcion="Descripción de la tarea", recompensa="Recompensa en monedas")
async def admin_agregar_tarea(interaction: discord.Interaction, nombre: str, descripcion: str, recompensa: int):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    if recompensa <= 0:
        await interaction.followup.send("La recompensa debe ser positiva.", ephemeral=True)
        return
    
    tarea_id = db.create_tarea(nombre, descripcion, recompensa)
    await interaction.followup.send(f"✅ Tarea **{nombre}** creada (ID: {tarea_id}). Recompensa: {recompensa} 🪙")

@bot.tree.command(name="admin_modificar_tarea", description="[ADMIN] Modifica una tarea")
@app_commands.describe(tarea_id="ID de la tarea", nombre="Nuevo nombre", descripcion="Nueva descripción", recompensa="Nueva recompensa")
async def admin_modificar_tarea(interaction: discord.Interaction, tarea_id: int, nombre: str = None, descripcion: str = None, recompensa: int = None):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    tarea = db.get_tarea(tarea_id)
    if not tarea:
        await interaction.followup.send("No se encontró esa tarea.", ephemeral=True)
        return
    
    if recompensa is not None and recompensa <= 0:
        await interaction.followup.send("La recompensa debe ser positiva.", ephemeral=True)
        return
    
    if db.update_tarea(tarea_id, nombre, descripcion, recompensa):
        await interaction.followup.send(f"✅ Tarea **{tarea['nombre']}** modificada.")
    else:
        await interaction.followup.send("No se realizaron cambios.", ephemeral=True)

@bot.tree.command(name="admin_eliminar_tarea", description="[ADMIN] Elimina una tarea")
@app_commands.describe(tarea_id="ID de la tarea")
async def admin_eliminar_tarea(interaction: discord.Interaction, tarea_id: int):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    tarea = db.get_tarea(tarea_id)
    if not tarea:
        await interaction.followup.send("No se encontró esa tarea.", ephemeral=True)
        return
    
    if db.delete_tarea(tarea_id):
        await interaction.followup.send(f"🗑️ Tarea **{tarea['nombre']}** eliminada.")
    else:
        await interaction.followup.send("Error al eliminar la tarea.", ephemeral=True)

@bot.tree.command(name="admin_ver_solicitudes_tareas", description="[ADMIN] Ver solicitudes de tareas pendientes")
async def admin_ver_solicitudes_tareas(interaction: discord.Interaction):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    submissions = db.get_pending_tarea_submissions()
    view = PendingSubmissionsPaginatorView(submissions, interaction.user.id)
    await interaction.followup.send(embed=view.get_embed(), view=view)

@bot.tree.command(name="admin_aceptar_tarea", description="[ADMIN] Acepta una solicitud de tarea")
@app_commands.describe(solicitud_id="ID de la solicitud")
async def admin_aceptar_tarea(interaction: discord.Interaction, solicitud_id: int):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    submission = db.get_tarea_submission(solicitud_id)
    if not submission:
        await interaction.followup.send("Solicitud no encontrada.", ephemeral=True)
        return
    
    if submission['estado'] != 'pendiente':
        await interaction.followup.send("Esta solicitud ya fue procesada.", ephemeral=True)
        return
    
    result = db.approve_tarea_submission(solicitud_id)
    if result:
        await interaction.followup.send(f"✅ Tarea **{submission['tarea_nombre']}** aprobada. Se han dado **{result['recompensa']} 🪙** a **{submission['username']}**.")
        try:
            user = await bot.fetch_user(submission['jugador_id'])
            await user.send(f"🎉 Tu tarea **{submission['tarea_nombre']}** ha sido aprobada. Has ganado **{result['recompensa']} 🪙**!")
        except:
            pass
    else:
        await interaction.followup.send("Error al procesar la solicitud.", ephemeral=True)

@bot.tree.command(name="admin_rechazar_tarea", description="[ADMIN] Rechaza una solicitud de tarea")
@app_commands.describe(solicitud_id="ID de la solicitud")
async def admin_rechazar_tarea(interaction: discord.Interaction, solicitud_id: int):
    await interaction.response.defer()
    ensure_player_registered(interaction.user.id, interaction.user.display_name)
    
    if not admin_only(interaction.user.id):
        await interaction.followup.send("No tienes permisos de administrador.", ephemeral=True)
        return
    
    submission = db.get_tarea_submission(solicitud_id)
    if not submission:
        await interaction.followup.send("Solicitud no encontrada.", ephemeral=True)
        return
    
    if submission['estado'] != 'pendiente':
        await interaction.followup.send("Esta solicitud ya fue procesada.", ephemeral=True)
        return
    
    if db.reject_tarea_submission(solicitud_id):
        await interaction.followup.send(f"❌ Tarea **{submission['tarea_nombre']}** de **{submission['username']}** rechazada.")
        try:
            user = await bot.fetch_user(submission['jugador_id'])
            await user.send(f"😔 Tu tarea **{submission['tarea_nombre']}** ha sido rechazada.")
        except:
            pass
    else:
        await interaction.followup.send("Error al procesar la solicitud.", ephemeral=True)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN no está configurado")
        exit(1)
    bot.run(DISCORD_TOKEN)
    print(">>> client.run ejecutándose")
