import discord
from typing import Callable, Any, Optional

class ConfirmView(discord.ui.View):
    def __init__(self, user_id: int, on_confirm: Callable, on_cancel: Callable = None, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Esta confirmación no es para ti.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Sí", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await self.on_confirm(interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        if self.on_cancel:
            await self.on_cancel(interaction)
        else:
            await interaction.response.edit_message(content="Acción cancelada.", view=None, embed=None)

    async def on_timeout(self):
        self.stop()


class StorePaginatorView(discord.ui.View):
    def __init__(self, items: list, user_id: int, items_per_page: int = 5, timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self.items = items
        self.user_id = user_id
        self.items_per_page = items_per_page
        self.current_page = 0
        self.max_pages = (len(items) - 1) // items_per_page + 1 if items else 1
        self.update_buttons()

    def update_buttons(self):
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.max_pages - 1
        self.last_page.disabled = self.current_page >= self.max_pages - 1

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🏪 Tienda de Piezas del Belén",
            description="Compra piezas para decorar tu belén.",
            color=discord.Color.gold()
        )
        
        if not self.items:
            embed.add_field(name="Sin productos", value="La tienda está vacía.", inline=False)
        else:
            start = self.current_page * self.items_per_page
            end = start + self.items_per_page
            page_items = self.items[start:end]
            
            for item in page_items:
                emoji = item.get('emoji', '🎁')
                nombre = item['nombre']
                precio = item['precio']
                desc = item.get('descripcion', 'Sin descripción')
                embed.add_field(
                    name=f"{emoji} {nombre} (ID: {item['id']})",
                    value=f"**Precio:** {precio} 🪙\n{desc}",
                    inline=False
                )
        
        embed.set_footer(text=f"Página {self.current_page + 1}/{self.max_pages} | Usa /tienda_comprar para comprar")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Este menú no es para ti.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.max_pages - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.max_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def on_timeout(self):
        self.stop()


class TasksPaginatorView(discord.ui.View):
    def __init__(self, tasks: list, user_id: int, items_per_page: int = 5, timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self.tasks = tasks
        self.user_id = user_id
        self.items_per_page = items_per_page
        self.current_page = 0
        self.max_pages = (len(tasks) - 1) // items_per_page + 1 if tasks else 1
        self.update_buttons()

    def update_buttons(self):
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.max_pages - 1
        self.last_page.disabled = self.current_page >= self.max_pages - 1

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📋 Tareas Disponibles",
            description="Completa tareas para ganar monedas.",
            color=discord.Color.blue()
        )
        
        if not self.tasks:
            embed.add_field(name="Sin tareas", value="No hay tareas disponibles para ti.", inline=False)
        else:
            start = self.current_page * self.items_per_page
            end = start + self.items_per_page
            page_tasks = self.tasks[start:end]
            
            for task in page_tasks:
                nombre = task['nombre']
                recompensa = task['recompensa']
                desc = task.get('descripcion', 'Sin descripción')
                embed.add_field(
                    name=f"📝 {nombre} (ID: {task['id']})",
                    value=f"**Recompensa:** {recompensa} 🪙\n{desc}",
                    inline=False
                )
        
        embed.set_footer(text=f"Página {self.current_page + 1}/{self.max_pages} | Usa /agregar_tarea para enviar")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Este menú no es para ti.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.max_pages - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.max_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def on_timeout(self):
        self.stop()


class PendingSubmissionsPaginatorView(discord.ui.View):
    def __init__(self, submissions: list, user_id: int, items_per_page: int = 5, timeout: float = 120.0):
        super().__init__(timeout=timeout)
        self.submissions = submissions
        self.user_id = user_id
        self.items_per_page = items_per_page
        self.current_page = 0
        self.max_pages = (len(submissions) - 1) // items_per_page + 1 if submissions else 1
        self.update_buttons()

    def update_buttons(self):
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.max_pages - 1
        self.last_page.disabled = self.current_page >= self.max_pages - 1

    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📋 Solicitudes de Tareas Pendientes",
            description="Revisa y aprueba/rechaza las tareas completadas.",
            color=discord.Color.orange()
        )
        
        if not self.submissions:
            embed.add_field(name="Sin solicitudes", value="No hay solicitudes pendientes.", inline=False)
        else:
            start = self.current_page * self.items_per_page
            end = start + self.items_per_page
            page_subs = self.submissions[start:end]
            
            for sub in page_subs:
                nota = sub.get('nota', 'Sin nota')
                embed.add_field(
                    name=f"ID: {sub['id']} | {sub['tarea_nombre']}",
                    value=f"**Usuario:** {sub['username']}\n**Recompensa:** {sub['recompensa']} 🪙\n**Nota:** {nota}",
                    inline=False
                )
        
        embed.set_footer(text=f"Página {self.current_page + 1}/{self.max_pages} | Usa /admin_aceptar_tarea o /admin_rechazar_tarea")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Este menú no es para ti.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.max_pages - 1, self.current_page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.max_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def on_timeout(self):
        self.stop()
