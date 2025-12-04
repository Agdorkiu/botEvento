import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")

@contextmanager
def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def jugador_existe(user_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM jugadores WHERE id = %s", (user_id,))
            return cur.fetchone() is not None

def registrar_jugador(user_id: int, username: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO jugadores (id, username, monedas) VALUES (%s, %s, 0) ON CONFLICT (id) DO NOTHING",
                (user_id, username)
            )

def actualizar_username(user_id: int, username: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jugadores SET username = %s WHERE id = %s",
                (username, user_id)
            )

def ensure_player(user_id: int, username: str) -> None:
    if not jugador_existe(user_id):
        registrar_jugador(user_id, username)
    else:
        actualizar_username(user_id, username)

def is_admin(user_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM administradores WHERE id = %s", (user_id,))
            return cur.fetchone() is not None

def is_blocked(user_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM usuarios_bloqueados WHERE id = %s", (user_id,))
            return cur.fetchone() is not None

def get_monedas(user_id: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT monedas FROM jugadores WHERE id = %s", (user_id,))
            result = cur.fetchone()
            return result[0] if result else 0

def update_monedas(user_id: int, delta: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jugadores SET monedas = monedas + %s WHERE id = %s RETURNING monedas",
                (delta, user_id)
            )
            result = cur.fetchone()
            return result[0] if result else 0

def add_admin(user_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO administradores (id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (user_id,)
                )
                return cur.rowcount > 0
            except:
                return False

def remove_admin(user_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM administradores WHERE id = %s", (user_id,))
            return cur.rowcount > 0

def block_user(user_id: int, reason: str = None) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO usuarios_bloqueados (id, reason) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (user_id, reason)
                )
                return cur.rowcount > 0
            except:
                return False

def unblock_user(user_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM usuarios_bloqueados WHERE id = %s", (user_id,))
            return cur.rowcount > 0

def find_belen(identifier: str):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if identifier.isdigit():
                cur.execute("SELECT * FROM belenes WHERE id = %s", (int(identifier),))
            else:
                cur.execute("SELECT * FROM belenes WHERE LOWER(nombre) = LOWER(%s)", (identifier,))
            return cur.fetchone()

def get_user_belen(user_id: int):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT b.* FROM belenes b
                JOIN miembros_belen mb ON b.id = mb.belen_id
                WHERE mb.jugador_id = %s
            """, (user_id,))
            return cur.fetchone()

def create_belen(nombre: str, creador_id: int, descripcion: str = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO belenes (nombre, creador_id, descripcion) VALUES (%s, %s, %s) RETURNING id",
                (nombre, creador_id, descripcion)
            )
            belen_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO miembros_belen (belen_id, jugador_id) VALUES (%s, %s)",
                (belen_id, creador_id)
            )
            return belen_id

def delete_belen(belen_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM belenes WHERE id = %s", (belen_id,))
            return cur.rowcount > 0

def add_member_to_belen(belen_id: int, jugador_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO miembros_belen (belen_id, jugador_id) VALUES (%s, %s)",
                    (belen_id, jugador_id)
                )
                return True
            except:
                return False

def leave_belen(jugador_id: int) -> dict:
    belen = get_user_belen(jugador_id)
    if not belen:
        return None
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            if belen['creador_id'] == jugador_id:
                cur.execute("DELETE FROM belenes WHERE id = %s", (belen['id'],))
                return {'deleted': True, 'belen': belen}
            else:
                cur.execute(
                    "DELETE FROM miembros_belen WHERE belen_id = %s AND jugador_id = %s",
                    (belen['id'], jugador_id)
                )
                return {'deleted': False, 'belen': belen}

def create_join_request(belen_id: int, jugador_id: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO solicitudes_union (belen_id, jugador_id, estado) 
                   VALUES (%s, %s, 'pendiente') 
                   ON CONFLICT (belen_id, jugador_id) DO UPDATE SET estado = 'pendiente', created_at = CURRENT_TIMESTAMP
                   RETURNING id""",
                (belen_id, jugador_id)
            )
            return cur.fetchone()[0]

def get_join_request(request_id: int):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT s.*, b.nombre as belen_nombre, b.creador_id, j.username
                FROM solicitudes_union s
                JOIN belenes b ON s.belen_id = b.id
                JOIN jugadores j ON s.jugador_id = j.id
                WHERE s.id = %s
            """, (request_id,))
            return cur.fetchone()

def get_pending_requests_for_belen(belen_id: int):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT s.*, j.username
                FROM solicitudes_union s
                JOIN jugadores j ON s.jugador_id = j.id
                WHERE s.belen_id = %s AND s.estado = 'pendiente'
                ORDER BY s.created_at
            """, (belen_id,))
            return cur.fetchall()

def accept_join_request(request_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE solicitudes_union SET estado = 'aceptada' WHERE id = %s AND estado = 'pendiente' RETURNING belen_id, jugador_id",
                (request_id,)
            )
            result = cur.fetchone()
            if result:
                belen_id, jugador_id = result
                cur.execute(
                    "INSERT INTO miembros_belen (belen_id, jugador_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (belen_id, jugador_id)
                )
                return True
            return False

def reject_join_request(request_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE solicitudes_union SET estado = 'rechazada' WHERE id = %s AND estado = 'pendiente'",
                (request_id,)
            )
            return cur.rowcount > 0

def list_store_items():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM piezas_catalogo ORDER BY precio")
            return cur.fetchall()

def get_store_item(identifier: str):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if identifier.isdigit():
                cur.execute("SELECT * FROM piezas_catalogo WHERE id = %s", (int(identifier),))
            else:
                cur.execute("SELECT * FROM piezas_catalogo WHERE LOWER(nombre) = LOWER(%s)", (identifier,))
            return cur.fetchone()

def create_store_item(nombre: str, precio: int, descripcion: str = None, emoji: str = '🎁') -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO piezas_catalogo (nombre, precio, descripcion, emoji) VALUES (%s, %s, %s, %s) RETURNING id",
                (nombre, precio, descripcion, emoji)
            )
            return cur.fetchone()[0]

def update_store_item(item_id: int, nombre: str = None, precio: int = None, descripcion: str = None, emoji: str = None) -> bool:
    updates = []
    params = []
    if nombre is not None:
        updates.append("nombre = %s")
        params.append(nombre)
    if precio is not None:
        updates.append("precio = %s")
        params.append(precio)
    if descripcion is not None:
        updates.append("descripcion = %s")
        params.append(descripcion)
    if emoji is not None:
        updates.append("emoji = %s")
        params.append(emoji)
    
    if not updates:
        return False
    
    params.append(item_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE piezas_catalogo SET {', '.join(updates)} WHERE id = %s", params)
            return cur.rowcount > 0

def delete_store_item(item_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM piezas_catalogo WHERE id = %s", (item_id,))
            return cur.rowcount > 0

def record_purchase(belen_id: int, pieza_id: int, comprador_id: int, cantidad: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO piezas_belen (belen_id, pieza_id, comprador_id, cantidad) VALUES (%s, %s, %s, %s)",
                (belen_id, pieza_id, comprador_id, cantidad)
            )
            return True

def get_belen_pieces(belen_id: int):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT pc.nombre, pc.emoji, pb.cantidad, j.username as comprador
                FROM piezas_belen pb
                JOIN piezas_catalogo pc ON pb.pieza_id = pc.id
                JOIN jugadores j ON pb.comprador_id = j.id
                WHERE pb.belen_id = %s
                ORDER BY pb.purchased_at DESC
            """, (belen_id,))
            return cur.fetchall()

def get_belen_members(belen_id: int):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT j.id, j.username, 
                       COALESCE(SUM(pb.cantidad * pc.precio), 0) as contribucion
                FROM miembros_belen mb
                JOIN jugadores j ON mb.jugador_id = j.id
                LEFT JOIN piezas_belen pb ON pb.comprador_id = j.id AND pb.belen_id = mb.belen_id
                LEFT JOIN piezas_catalogo pc ON pb.pieza_id = pc.id
                WHERE mb.belen_id = %s
                GROUP BY j.id, j.username
                ORDER BY contribucion DESC
            """, (belen_id,))
            return cur.fetchall()

def list_tareas():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tareas ORDER BY recompensa DESC")
            return cur.fetchall()

def get_tarea(tarea_id: int):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tareas WHERE id = %s", (tarea_id,))
            return cur.fetchone()

def get_available_tareas(user_id: int):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.* FROM tareas t
                WHERE NOT EXISTS (
                    SELECT 1 FROM tareas_completadas tc 
                    WHERE tc.tarea_id = t.id 
                    AND tc.jugador_id = %s 
                    AND tc.estado = 'aprobada'
                )
                ORDER BY t.recompensa DESC
            """, (user_id,))
            return cur.fetchall()

def create_tarea(nombre: str, descripcion: str, recompensa: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tareas (nombre, descripcion, recompensa) VALUES (%s, %s, %s) RETURNING id",
                (nombre, descripcion, recompensa)
            )
            return cur.fetchone()[0]

def update_tarea(tarea_id: int, nombre: str = None, descripcion: str = None, recompensa: int = None) -> bool:
    updates = []
    params = []
    if nombre is not None:
        updates.append("nombre = %s")
        params.append(nombre)
    if descripcion is not None:
        updates.append("descripcion = %s")
        params.append(descripcion)
    if recompensa is not None:
        updates.append("recompensa = %s")
        params.append(recompensa)
    
    if not updates:
        return False
    
    params.append(tarea_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE tareas SET {', '.join(updates)} WHERE id = %s", params)
            return cur.rowcount > 0

def delete_tarea(tarea_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tareas WHERE id = %s", (tarea_id,))
            return cur.rowcount > 0

def submit_tarea(tarea_id: int, jugador_id: int, nota: str = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tareas_completadas (tarea_id, jugador_id, nota, estado) VALUES (%s, %s, %s, 'pendiente') RETURNING id",
                (tarea_id, jugador_id, nota)
            )
            return cur.fetchone()[0]

def get_pending_tarea_submissions():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT tc.*, t.nombre as tarea_nombre, t.recompensa, j.username
                FROM tareas_completadas tc
                JOIN tareas t ON tc.tarea_id = t.id
                JOIN jugadores j ON tc.jugador_id = j.id
                WHERE tc.estado = 'pendiente'
                ORDER BY tc.created_at
            """)
            return cur.fetchall()

def get_tarea_submission(submission_id: int):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT tc.*, t.nombre as tarea_nombre, t.recompensa, j.username
                FROM tareas_completadas tc
                JOIN tareas t ON tc.tarea_id = t.id
                JOIN jugadores j ON tc.jugador_id = j.id
                WHERE tc.id = %s
            """, (submission_id,))
            return cur.fetchone()

def approve_tarea_submission(submission_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE tareas_completadas SET estado = 'aprobada', reviewed_at = CURRENT_TIMESTAMP
                WHERE id = %s AND estado = 'pendiente'
                RETURNING tarea_id, jugador_id
            """, (submission_id,))
            result = cur.fetchone()
            if result:
                cur.execute("SELECT recompensa FROM tareas WHERE id = %s", (result['tarea_id'],))
                tarea = cur.fetchone()
                if tarea:
                    cur.execute(
                        "UPDATE jugadores SET monedas = monedas + %s WHERE id = %s RETURNING monedas",
                        (tarea['recompensa'], result['jugador_id'])
                    )
                    return {'recompensa': tarea['recompensa'], 'jugador_id': result['jugador_id']}
            return None

def reject_tarea_submission(submission_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tareas_completadas SET estado = 'rechazada', reviewed_at = CURRENT_TIMESTAMP WHERE id = %s AND estado = 'pendiente'",
                (submission_id,)
            )
            return cur.rowcount > 0

def has_pending_submission(tarea_id: int, jugador_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM tareas_completadas WHERE tarea_id = %s AND jugador_id = %s AND estado = 'pendiente'",
                (tarea_id, jugador_id)
            )
            return cur.fetchone() is not None
