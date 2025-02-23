import streamlit as st
import os
import tempfile
from PIL import Image
import pandas as pd

def render_employee_page(api_client):
    """Renderiza página de funcionários"""
    try:
        st.title("LineGuard - Gestão de Funcionários")
        
        # Tabs para organizar o conteúdo
        tab1, tab2 = st.tabs(["Cadastrar Novo", "Funcionários Cadastrados"])
        
        # Tab de Cadastro
        with tab1:
            with st.form("employee_form", clear_on_submit=True):
                st.subheader("Dados do Funcionário")
                
                # Campos do formulário
                col1, col2 = st.columns(2)
                
                with col1:
                    employee_id = st.text_input(
                        "ID/Matrícula", 
                        help="Identificador único do funcionário"
                    )
                    name = st.text_input(
                        "Nome Completo",
                        help="Nome completo do funcionário"
                    )
                    
                with col2:
                    photo = st.file_uploader(
                        "Foto do Funcionário", 
                        type=["jpg", "jpeg", "png"],
                        help="Selecione uma foto clara do rosto, preferencialmente frontal"
                    )
                    
                    # Preview da foto
                    if photo:
                        try:
                            image = Image.open(photo)
                            st.image(image, caption="Preview da foto", width=200)
                        except Exception as e:
                            st.error(f"Erro ao carregar imagem: {str(e)}")
                
                # Botão de submit
                submit = st.form_submit_button("Cadastrar Funcionário", use_container_width=True)
                
                if submit:
                    if not all([employee_id, name, photo]):
                        st.error("❌ Todos os campos são obrigatórios!")
                    else:
                        result = api_client.create_employee(employee_id, name, photo)
                        if 'error' in result:
                            st.error(f"❌ Erro ao cadastrar: {result['error']}")
                        else:
                            st.success("✅ Funcionário cadastrado com sucesso!")
        
        # Tab de Listagem
        with tab2:
            st.subheader("Funcionários Cadastrados")
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                show_inactive = st.checkbox("Mostrar Inativos", value=False)
            with col2:
                search = st.text_input("Buscar por nome ou ID", "")
            
            # Buscar funcionários
            result = api_client.list_employees(active_only=not show_inactive)
            if 'error' in result:
                st.error(f"❌ Erro ao listar funcionários: {result['error']}")
                return
            
            employees = result.get('employees', [])
            
            # Filtrar por busca
            if search:
                search = search.lower()
                employees = [
                    emp for emp in employees 
                    if search in emp["name"].lower() 
                    or search in emp["employee_id"].lower()
                ]
            
            if not employees:
                st.info("Nenhum funcionário encontrado")
            else:
                # Lista de funcionários
                for emp in employees:
                    cols = st.columns([1, 3, 2, 1, 1])
                    
                    # Foto do funcionário
                    try:
                        if "photo_path" in emp and os.path.exists(emp["photo_path"]):
                            image = Image.open(emp["photo_path"])
                            cols[0].image(image, width=50)
                        else:
                            cols[0].write("🖼️")
                    except Exception:
                        cols[0].write("🖼️")
                    
                    # Informações básicas
                    cols[1].write(f"**{emp['name']}**")
                    cols[2].write(f"ID: {emp['employee_id']}")
                    
                    # Status
                    status = "✅ Ativo" if emp.get("active", False) else "❌ Inativo"
                    cols[3].write(status)
                    
                    # Ações
                    is_active = emp.get("active", False)
                    if is_active:
                        # Container para botões na mesma coluna
                        with cols[4]:
                            c1, c2 = st.columns(2)
                            if c1.button("✏️", key=f"edit_{emp['employee_id']}", help="Editar"):
                                st.session_state.editing_employee = emp
                                st.session_state.show_edit_form = True
                            if c2.button("🗑️", key=f"del_{emp['employee_id']}", help="Deletar"):
                                if api_client.delete_employee(emp["employee_id"]):
                                    st.success("✅ Funcionário desativado")
                                    st.rerun()
                    else:
                        if cols[4].button("♻️", key=f"act_{emp['employee_id']}", help="Reativar"):
                            if api_client.update_employee(emp["employee_id"], {"active": True}):
                                st.success("✅ Funcionário reativado")
                                st.rerun()
                    
                    st.markdown("---")
                
                # Formulário de edição
                if st.session_state.get("show_edit_form", False):
                    emp = st.session_state.editing_employee
                    st.subheader(f"Editar Funcionário: {emp['name']}")
                    
                    with st.form("edit_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            employee_id = st.text_input(
                                "ID/Matrícula",
                                value=emp["employee_id"],
                                disabled=True,  # ID não pode ser alterado
                                help="ID não pode ser alterado"
                            )
                            new_name = st.text_input(
                                "Nome",
                                value=emp["name"],
                                help="Nome completo do funcionário"
                            )
                        
                        with col2:
                            new_photo = st.file_uploader(
                                "Nova Foto",
                                type=["jpg", "jpeg", "png"],
                                help="Selecione uma nova foto do rosto, preferencialmente frontal"
                            )
                            
                            # Mostrar foto atual
                            if "photo_path" in emp and os.path.exists(emp["photo_path"]):
                                st.write("Foto Atual:")
                                image = Image.open(emp["photo_path"])
                                st.image(image, width=200)
                            
                            # Preview da nova foto
                            if new_photo:
                                st.write("Nova Foto:")
                                image = Image.open(new_photo)
                                st.image(image, width=200)
                        
                        col1, col2 = st.columns(2)
                        update = col1.form_submit_button("Atualizar")
                        cancel = col2.form_submit_button("Cancelar")
                        
                        if cancel:
                            st.session_state.show_edit_form = False
                            st.rerun()
                            
                        if update:
                            print(f"\n=== Frontend: Atualizando funcionário ===")
                            print(f"ID: {emp['employee_id']}")
                            print(f"Nome antigo: {emp['name']}")
                            print(f"Nome novo: {new_name}")  # Aqui está o nome novo
                            
                            # Atualizar usando novo método
                            if update_employee(api_client, emp["employee_id"], new_name, new_photo):
                                st.success("✅ Funcionário atualizado!")
                                st.session_state.show_edit_form = False
                                st.rerun()
    except Exception as e:
        st.error(f"❌ Erro ao renderizar página: {str(e)}")

def update_employee(api_client, employee_id: str, name: str, photo=None, active: bool = None):
    """Atualiza funcionário"""
    try:
        result = api_client.update_employee(
            employee_id=employee_id,
            name=name,  # Aqui está passando o nome correto
            photo=photo,
            active=active
        )
        if 'error' in result:
            st.error(f"❌ Erro ao atualizar: {result['error']}")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Erro ao atualizar: {str(e)}")
        return False 