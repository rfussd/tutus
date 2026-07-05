"""Unit tests for files_skill, memory_skill, and documents_skill modules.

External dependencies (os.startfile, Path.home) are mocked/isolated via
monkeypatch. Document libraries (docx, openpyxl, reportlab, pptx) are real
since they are installed; only os.startfile is mocked to avoid opening files.
The DB used by memory_skill is redirected to a temp DB via the temp_db fixture.
"""

from __future__ import annotations

import pathlib

import pytest

# ===========================================================================
# 1. TestFilesSkill — skills/files_skill.py
# ===========================================================================


class TestFilesSkill:
    """Verify is_safe_path, list_files, move_file, organize_downloads."""

    # -- is_safe_path (pure, no mocks needed) ------------------------------

    def test_is_safe_path_allows_workspace(self):
        from skills.files_skill import is_safe_path

        # CWD is the project root (not under AppData), so it is safe
        assert is_safe_path(pathlib.Path.cwd()) is True

    def test_is_safe_path_blocks_windows(self):
        from skills.files_skill import is_safe_path

        assert is_safe_path(pathlib.Path("C:/Windows")) is False
        assert is_safe_path(pathlib.Path("C:/Windows/System32")) is False

    def test_is_safe_path_blocks_program_files(self):
        from skills.files_skill import is_safe_path

        assert is_safe_path(pathlib.Path("C:/Program Files")) is False
        assert is_safe_path(pathlib.Path("C:/Program Files (x86)")) is False

    def test_is_safe_path_blocks_appdata(self):
        from skills.files_skill import is_safe_path

        assert is_safe_path(pathlib.Path.home() / "AppData" / "Local") is False

    # -- list_files ---------------------------------------------------------

    def test_list_files_unknown_folder(self):
        from skills.files_skill import list_files

        result = list_files("carpeta_inexistente_xyz")
        assert "no reconocida" in result

    def test_list_files_lists_contents(self, monkeypatch, tmp_path):
        import skills.files_skill as fs

        (tmp_path / "a.txt").write_text("x")
        (tmp_path / "b.txt").write_text("y")
        monkeypatch.setitem(fs.FOLDER_MAP, "testfld", tmp_path)

        result = fs.list_files("testfld")
        assert "Archivos en testfld" in result
        assert "a.txt" in result
        assert "b.txt" in result
        assert "(2)" in result

    def test_list_files_empty_folder(self, monkeypatch, tmp_path):
        import skills.files_skill as fs

        monkeypatch.setitem(fs.FOLDER_MAP, "emptyfld", tmp_path)

        result = fs.list_files("emptyfld")
        assert "vacía" in result

    def test_list_files_nonexistent_folder(self, monkeypatch, tmp_path):
        import skills.files_skill as fs

        monkeypatch.setitem(fs.FOLDER_MAP, "ghostfld", tmp_path / "ghost")

        result = fs.list_files("ghostfld")
        assert "no existe" in result

    def test_list_files_case_insensitive(self, monkeypatch, tmp_path):
        import skills.files_skill as fs

        (tmp_path / "x.txt").write_text("x")
        monkeypatch.setitem(fs.FOLDER_MAP, "mixcase", tmp_path)

        result = fs.list_files("MIXCASE")
        assert "Archivos en MIXCASE" in result
        assert "x.txt" in result

    # -- move_file ----------------------------------------------------------

    @pytest.fixture
    def tmp_home(self, monkeypatch, tmp_path):
        """Patch Path.home() to a temp dir so Downloads/Desktop are isolated."""
        home = tmp_path / "fake_home"
        (home / "Downloads").mkdir(parents=True)
        (home / "Desktop").mkdir(parents=True)
        monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: home))
        return home

    def test_move_file_unknown_destination(self, tmp_home):
        from skills.files_skill import move_file

        result = move_file("anything.txt", "destino_raro")
        assert "no permitido" in result

    def test_move_file_not_found(self, monkeypatch, tmp_home):
        import skills.files_skill as fs

        monkeypatch.setitem(fs.FOLDER_MAP, "dest", tmp_home / "dest")
        monkeypatch.setattr(fs, "FORBIDDEN_PATHS", [])

        result = fs.move_file("missing.txt", "dest")
        assert "No encontré" in result

    def test_move_file_success(self, monkeypatch, tmp_home):
        import skills.files_skill as fs

        src = tmp_home / "Downloads" / "note.txt"
        src.write_text("hello")
        dest_dir = tmp_home / "dest"
        dest_dir.mkdir()
        monkeypatch.setitem(fs.FOLDER_MAP, "dest", dest_dir)
        # tmp_path is under AppData which is_safe_path blocks; isolate it.
        monkeypatch.setattr(fs, "FORBIDDEN_PATHS", [])

        result = fs.move_file("note.txt", "dest")
        assert "Moví" in result
        assert "note.txt" in result
        assert (dest_dir / "note.txt").exists()
        assert not src.exists()

    def test_move_file_from_desktop(self, monkeypatch, tmp_home):
        import skills.files_skill as fs

        src = tmp_home / "Desktop" / "desk.txt"
        src.write_text("d")
        dest_dir = tmp_home / "dest2"
        dest_dir.mkdir()
        monkeypatch.setitem(fs.FOLDER_MAP, "dest2", dest_dir)
        monkeypatch.setattr(fs, "FORBIDDEN_PATHS", [])

        result = fs.move_file("desk.txt", "dest2")
        assert "Moví" in result
        assert (dest_dir / "desk.txt").exists()

    def test_move_file_blocked_path(self, monkeypatch, tmp_home):
        import skills.files_skill as fs

        src = tmp_home / "Downloads" / "note2.txt"
        src.write_text("hello")
        # Point destination at a forbidden path (AppData under home)
        forbidden_dest = tmp_home / "AppData"
        forbidden_dest.mkdir(exist_ok=True)
        monkeypatch.setitem(fs.FOLDER_MAP, "forbidden", forbidden_dest)

        result = fs.move_file("note2.txt", "forbidden")
        assert "no permitida" in result
        assert src.exists()  # not moved

    # -- organize_downloads -------------------------------------------------

    def test_organize_downloads_categorizes(self, tmp_home):
        import skills.files_skill as fs

        dl = tmp_home / "Downloads"
        (dl / "song.mp3").write_text("m")
        (dl / "doc.pdf").write_text("d")
        (dl / "pic.jpg").write_text("p")
        (dl / "archive.zip").write_text("z")
        (dl / "code.py").write_text("c")
        (dl / "weird.xyz").write_text("u")

        result = fs.organize_downloads()
        assert "Organicé 6 archivos" in result
        assert (dl / "Música" / "song.mp3").exists()
        assert (dl / "Documentos" / "doc.pdf").exists()
        assert (dl / "Imágenes" / "pic.jpg").exists()
        assert (dl / "Comprimidos" / "archive.zip").exists()
        assert (dl / "Código" / "code.py").exists()
        assert (dl / "Otros" / "weird.xyz").exists()

    def test_organize_downloads_empty(self, tmp_home):
        import skills.files_skill as fs

        result = fs.organize_downloads()
        assert "Organicé 0 archivos" in result

    def test_organize_downloads_skips_subdirectories(self, tmp_home):
        import skills.files_skill as fs

        dl = tmp_home / "Downloads"
        (dl / "subfolder").mkdir()
        (dl / "real.txt").write_text("r")

        result = fs.organize_downloads()
        assert "Organicé 1 archivos" in result
        assert (dl / "Documentos" / "real.txt").exists()


# ===========================================================================
# 2. TestMemorySkill — skills/memory_skill.py
# ===========================================================================


class TestMemorySkill:
    """Verify save_memory, search_memory, forget_memory, list_memories."""

    # -- save_memory --------------------------------------------------------

    def test_save_memory_empty_returns_message(self, temp_db):
        from skills.memory_skill import save_memory

        assert save_memory("   ") == "No hay nada que recordar."

    def test_save_memory_calls_underlying_save(self, temp_db):
        from skills.memory_skill import save_memory

        result = save_memory("reunión a las tres", domain="trabajo")
        assert result == "Recordado: reunión a las tres"

    def test_save_memory_reformats_first_person_soy(self, temp_db):
        from skills.memory_skill import save_memory

        result = save_memory("soy programador")
        assert "David es programador" in result

    def test_save_memory_reformats_me_gusta(self, temp_db):
        from skills.memory_skill import save_memory

        result = save_memory("me gusta el café")
        assert "a David le gusta el café" in result

    def test_save_memory_reformats_tengo(self, temp_db):
        from skills.memory_skill import save_memory

        result = save_memory("tengo 30 años")
        assert "David tiene 30 años" in result

    def test_save_memory_reformats_mi(self, temp_db):
        from skills.memory_skill import save_memory

        result = save_memory("mi perro es grande")
        assert "su perro es grande" in result

    def test_save_memory_music_short_prefix(self, temp_db):
        from skills.memory_skill import save_memory

        # 2 words + domain music -> "A David le gusta {content}"
        result = save_memory("bad bunny", domain="music")
        assert "A David le gusta bad bunny" in result

    def test_save_memory_music_long_no_prefix(self, temp_db):
        from skills.memory_skill import save_memory

        # >3 words, domain music -> no music prefix
        result = save_memory("una banda muy ruidosa", domain="music")
        assert "A David le gusta" not in result

    def test_save_memory_null_domain_normalized(self, temp_db):
        from skills.memory_skill import save_memory, search_memory

        save_memory("dato curioso", domain="null")
        # domain "null" normalized to "general" -> searchable under "general"
        result = search_memory("dato", domain="general")
        assert "Recuerdo:" in result
        assert "dato curioso" in result

    def test_save_memory_none_domain_normalized(self, temp_db):
        from skills.memory_skill import save_memory, search_memory

        save_memory("otro dato", domain="none")
        # domain "none" normalized to "general" -> searchable under "general"
        result = search_memory("otro", domain="general")
        assert "Recuerdo:" in result
        assert "otro dato" in result

    # -- search_memory ------------------------------------------------------

    def test_search_memory_no_results(self, temp_db):
        from skills.memory_skill import search_memory

        result = search_memory("cosainexistente12345")
        assert "No recuerdo nada" in result

    def test_search_memory_returns_matches(self, temp_db):
        from skills.memory_skill import save_memory, search_memory

        save_memory("compré pan en la mañana", domain="general")
        result = search_memory("pan")
        assert "Recuerdo:" in result
        assert "pan" in result
        assert "[general]" in result

    def test_search_memory_null_domain_normalized(self, temp_db):
        from skills.memory_skill import save_memory, search_memory

        save_memory("recuerdo general", domain="general")
        result = search_memory("recuerdo", domain="null")
        assert "Recuerdo:" in result

    def test_search_memory_domain_overrides_query(self, temp_db):
        from skills.memory_skill import save_memory, search_memory

        save_memory("algo en music", domain="music")
        save_memory("algo en general", domain="general")
        # With domain set, query is ignored and all of that domain is returned
        result = search_memory("zzznoqueryzzz", domain="music")
        assert "algo en music" in result
        assert "algo en general" not in result

    def test_search_memory_identity_query_clears_query(self, temp_db):
        from skills.memory_skill import save_memory, search_memory

        save_memory("David es alto", domain="general")
        # "quién" is an identity term -> query becomes "" -> returns recent memories
        result = search_memory("quién soy")
        assert "Recuerdo:" in result
        assert "David es alto" in result

    # -- forget_memory ------------------------------------------------------

    def test_forget_memory_empty_query(self, temp_db):
        from skills.memory_skill import forget_memory

        assert forget_memory("   ") == "¿Qué quieres que olvide?"

    def test_forget_memory_deletes(self, temp_db):
        from skills.memory_skill import forget_memory, save_memory, search_memory

        save_memory("dato a olvidar xyz", domain="general")
        result = forget_memory("olvidar")
        assert "Olvidé" in result
        # After forget, search should not find it
        assert "No recuerdo nada" in search_memory("olvidar")

    def test_forget_memory_with_domain(self, temp_db):
        from skills.memory_skill import forget_memory, save_memory

        save_memory("secreto xyz", domain="privado")
        result = forget_memory("secreto", domain="privado")
        assert "Olvidé 1 recuerdos" in result

    # -- list_memories ------------------------------------------------------

    def test_list_memories_empty(self, temp_db):
        from skills.memory_skill import list_memories

        assert list_memories() == "No tengo recuerdos guardados."

    def test_list_memories_returns_count(self, temp_db):
        from skills.memory_skill import list_memories, save_memory

        save_memory("recuerdo uno", domain="general")
        save_memory("recuerdo dos", domain="trabajo")
        result = list_memories()
        assert "Mis recuerdos (2)" in result
        assert "recuerdo uno" in result
        assert "recuerdo dos" in result

    def test_list_memories_filtered_by_domain(self, temp_db):
        from skills.memory_skill import list_memories, save_memory

        save_memory("item music", domain="music")
        save_memory("item general", domain="general")
        result = list_memories(domain="music")
        assert "item music" in result
        assert "item general" not in result


# ===========================================================================
# 3. TestDocumentsSkill — skills/documents_skill.py
# ===========================================================================


class TestDocumentsSkill:
    """Verify create_word/excel/pdf/pptx with mocked os.startfile + tmp DOCS_PATH."""

    @pytest.fixture
    def docs_tmp(self, monkeypatch, tmp_path):
        """Redirect DOCS_PATH to a temp dir and mock os.startfile."""
        import skills.documents_skill as ds

        tmp_docs = tmp_path / "documents"
        tmp_docs.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(ds, "DOCS_PATH", tmp_docs)
        return tmp_docs

    @pytest.fixture
    def mock_startfile(self, monkeypatch):
        """Mock os.startfile and record calls."""
        called = []
        monkeypatch.setattr("os.startfile", lambda p: called.append(p))
        return called

    # -- create_word --------------------------------------------------------

    def test_create_word_creates_file(self, docs_tmp, mock_startfile):
        from skills.documents_skill import create_word

        result = create_word("test_word", "Línea uno\nLínea dos")
        assert result == "Word creado: test_word.docx"
        out = docs_tmp / "test_word.docx"
        assert out.exists()
        assert out.stat().st_size > 0
        assert len(mock_startfile) == 1
        assert pathlib.Path(mock_startfile[0]) == out

    def test_create_word_error_propagates(self, docs_tmp, mock_startfile, monkeypatch):
        from skills.documents_skill import create_word

        def boom(*a, **kw):
            raise RuntimeError("docx init failed")

        monkeypatch.setattr("docx.Document", boom)
        with pytest.raises(RuntimeError, match="docx init failed"):
            create_word("err_word", "x")

    # -- create_excel -------------------------------------------------------

    def test_create_excel_creates_file(self, docs_tmp, mock_startfile):
        from skills.documents_skill import create_excel

        result = create_excel("test_excel", "A,B,C\n1,2,3\n4,5,6")
        assert result == "Excel creado: test_excel.xlsx"
        out = docs_tmp / "test_excel.xlsx"
        assert out.exists()
        assert out.stat().st_size > 0
        assert len(mock_startfile) == 1

    def test_create_excel_error_propagates(self, docs_tmp, mock_startfile, monkeypatch):
        from skills.documents_skill import create_excel

        def boom(*a, **kw):
            raise RuntimeError("openpyxl failed")

        monkeypatch.setattr("openpyxl.Workbook", boom)
        with pytest.raises(RuntimeError, match="openpyxl failed"):
            create_excel("err_excel", "a,b")

    # -- create_pdf ---------------------------------------------------------

    def test_create_pdf_creates_file(self, docs_tmp, mock_startfile):
        from skills.documents_skill import create_pdf

        result = create_pdf("test_pdf", "Párrafo uno\nPárrafo dos")
        assert result == "PDF creado: test_pdf.pdf"
        out = docs_tmp / "test_pdf.pdf"
        assert out.exists()
        assert out.stat().st_size > 0
        assert len(mock_startfile) == 1

    def test_create_pdf_error_propagates(self, docs_tmp, mock_startfile, monkeypatch):
        import skills.documents_skill as ds

        def boom(*a, **kw):
            raise RuntimeError("reportlab failed")

        # SimpleDocTemplate is imported inside create_pdf; patch via module attr
        monkeypatch.setattr("reportlab.platypus.SimpleDocTemplate", boom)
        with pytest.raises(RuntimeError, match="reportlab failed"):
            ds.create_pdf("err_pdf", "x")

    # -- create_pptx --------------------------------------------------------

    def test_create_pptx_creates_file(self, docs_tmp, mock_startfile):
        from skills.documents_skill import create_pptx

        content = "Subtítulo demo\nTítulo 1|Punto A·Punto B\nTítulo 2|Texto único"
        result = create_pptx("test_pptx", content)
        assert result == "Presentación creada: test_pptx.pptx"
        out = docs_tmp / "test_pptx.pptx"
        assert out.exists()
        assert out.stat().st_size > 0
        assert len(mock_startfile) == 1

    def test_create_pptx_single_line(self, docs_tmp, mock_startfile):
        from skills.documents_skill import create_pptx

        # Only one line -> title slide only, no content slides
        result = create_pptx("single", "Solo subtítulo")
        assert result == "Presentación creada: single.pptx"
        assert (docs_tmp / "single.pptx").exists()

    def test_create_pptx_error_propagates(self, docs_tmp, mock_startfile, monkeypatch):
        from skills.documents_skill import create_pptx

        def boom(*a, **kw):
            raise RuntimeError("pptx failed")

        monkeypatch.setattr("pptx.Presentation", boom)
        with pytest.raises(RuntimeError, match="pptx failed"):
            create_pptx("err_pptx", "x")
