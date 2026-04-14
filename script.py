# -*- coding: utf-8 -*-

import arcpy
import os

# ============================================================
# ENTRADAS — vem da interface da tool
# ============================================================

pontos      = arcpy.GetParameterAsText(0)
pasta_saida = arcpy.GetParameterAsText(1)
sistema_ref = arcpy.GetParameter(2)

# ============================================================
# RASTERS FIXOS — nao aparecem na interface
# ============================================================

accum_to  = r"S:\Outorga\VETORES_OUTORGA\AUT_REGIONALIZACAO\SRTM.gdb\accum_to"
direct_to = r"S:\Outorga\VETORES_OUTORGA\AUT_REGIONALIZACAO\SRTM.gdb\direct_to"

# ============================================================
# CONFIGURACOES
# ============================================================

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

# ============================================================
# PASSO 1 — confirma pasta de saida
# ============================================================

if not os.path.exists(pasta_saida):
    arcpy.AddError("Pasta de saida nao encontrada: " + pasta_saida)
    raise SystemExit

arcpy.AddMessage("Pasta de saida: " + pasta_saida)

# ============================================================
# PASSO 2 — resolucao do raster
# ============================================================

resolucao_texto = arcpy.GetRasterProperties_management(
    accum_to, "CELLSIZEX").getOutput(0)

resolucao = float(resolucao_texto.replace(",", "."))
arcpy.AddMessage("Resolucao do raster: " + str(resolucao))

# ============================================================
# PASSO 3 — salva pontos como shapefile e conta
# ============================================================

pontos_shp = os.path.join(pasta_saida, "pontos_entrada.shp")
arcpy.CopyFeatures_management(pontos, pontos_shp)

total_pontos = int(arcpy.GetCount_management(pontos_shp).getOutput(0))
arcpy.AddMessage("Total de pontos: " + str(total_pontos))

# ============================================================
# PASSO 4 — loop principal
# ============================================================

contador    = 0
shps_finais = []
dados_hidro = []  # coleta lat, lon, area para o HidroAPI

with arcpy.da.SearchCursor(pontos_shp, ["OID@", "SHAPE@XY"]) as cursor:
    for row in cursor:

        id_ponto  = row[0]
        contador += 1

        arcpy.AddMessage("")
        arcpy.AddMessage("Processando ponto " + str(contador) + " de " + str(total_pontos))
        arcpy.AddMessage("ID: " + str(id_ponto))

        # ── 4a — copia o ponto ────────────────────────────────

        ponto_temp = os.path.join(pasta_saida, "tmp_ponto_" + str(id_ponto) + ".shp")

        arcpy.Select_analysis(
            pontos_shp,
            ponto_temp,
            '"FID" = ' + str(id_ponto)
        )

        # ── 4b — define SR se desconhecido ────────────────────

        sr_ponto = arcpy.Describe(ponto_temp).spatialReference

        if sr_ponto.name == "Unknown":
            arcpy.AddMessage("  SR desconhecido — assumindo SR do raster...")
            sr_raster = arcpy.Describe(accum_to).spatialReference
            arcpy.DefineProjection_management(ponto_temp, sr_raster)

        # ── 4c — snap pour point ──────────────────────────────

        arcpy.AddMessage("  Aplicando Snap Pour Point...")

        snap_saida = os.path.join(pasta_saida, "snap_" + str(id_ponto) + ".tif")

        arcpy.gp.SnapPourPoint_sa(
            ponto_temp,
            accum_to,
            snap_saida,
            0,
            "FID"
        )

        # ── 4d — watershed ────────────────────────────────────

        arcpy.AddMessage("  Delimitando bacia...")

        bacia_raster = os.path.join(pasta_saida, "bacia_" + str(id_ponto) + ".tif")

        parallel_anterior = arcpy.env.parallelProcessingFactor
        arcpy.env.parallelProcessingFactor = "0"

        arcpy.gp.Watershed_sa(
            direct_to,
            snap_saida,
            bacia_raster
        )

        arcpy.env.parallelProcessingFactor = parallel_anterior

        # ── 4e — raster para poligono ─────────────────────────

        arcpy.AddMessage("  Convertendo para vetor...")

        bacia_poligono = os.path.join(pasta_saida, "tmp_poligono_" + str(id_ponto) + ".shp")

        arcpy.RasterToPolygon_conversion(
            bacia_raster,
            bacia_poligono,
            "NO_SIMPLIFY",
            "VALUE"
        )

        # ── 4f — dissolve ─────────────────────────────────────

        arcpy.AddMessage("  Dissolvendo...")

        bacia_dissolv = os.path.join(pasta_saida, "tmp_dissolv_" + str(id_ponto) + ".shp")

        arcpy.Dissolve_management(
            bacia_poligono,
            bacia_dissolv
        )

        # ── 4g — suavizar poligono ────────────────────────────

        arcpy.AddMessage("  Suavizando poligono...")

        bacia_smooth = os.path.join(pasta_saida, "tmp_smooth_" + str(id_ponto) + ".shp")

        arcpy.SmoothPolygon_cartography(
            bacia_dissolv,
            bacia_smooth,
            "PAEK",
            "300 Meters"
        )

        # ── 4h — reprojetar para sistema selecionado ──────────

        arcpy.AddMessage("  Reprojetando...")

        bacia_final = os.path.join(pasta_saida, "bacia_" + str(id_ponto) + "_final.shp")

        arcpy.Project_management(
            bacia_smooth,
            bacia_final,
            sistema_ref
        )

        # ── 4i — calcular area em km2 ─────────────────────────

        arcpy.AddMessage("  Calculando area...")

        campo_area = "AREA_KM2"

        if campo_area not in [f.name for f in arcpy.ListFields(bacia_final)]:
            arcpy.AddField_management(bacia_final, campo_area, "DOUBLE")

        area_final = 0
        with arcpy.da.UpdateCursor(bacia_final, ["SHAPE@AREA", campo_area]) as cur_area:
            for linha in cur_area:
                area_final = round(linha[0] / 1000000, 4)
                linha[1]   = area_final
                cur_area.updateRow(linha)

        arcpy.AddMessage("  Area: " + str(area_final) + " km2")

        # ── 4j-pre — coleta coordenadas WGS84 para HidroAPI ──

        sr_wgs84 = arcpy.SpatialReference(4326)
        with arcpy.da.SearchCursor(ponto_temp, ["SHAPE@"], spatial_reference=sr_wgs84) as cur_wgs:
            for linha_wgs in cur_wgs:
                pt_geom = linha_wgs[0].firstPoint
                dados_hidro.append({
                    "lat": round(pt_geom.Y, 6),
                    "lon": round(pt_geom.X, 6),
                    "area": area_final
                })

        # ── 4j — apaga temporarios ────────────────────────────

        arcpy.AddMessage("  Limpando temporarios...")

        for tmp in [ponto_temp, bacia_raster, bacia_poligono, bacia_dissolv, bacia_smooth]:
            if arcpy.Exists(tmp):
                arcpy.Delete_management(tmp)

        shps_finais.append(bacia_final)
        arcpy.AddMessage("  Ponto " + str(id_ponto) + " concluido.")

# ============================================================
# PASSO 5 — merge de todos os resultados
# ============================================================

bacia_completa = None

if len(shps_finais) > 1:
    arcpy.AddMessage("")
    arcpy.AddMessage("Juntando resultados...")
    bacia_completa = os.path.join(pasta_saida, "bacias_todas.shp")
    arcpy.Merge_management(shps_finais, bacia_completa)
    arcpy.AddMessage("Arquivo final: bacias_todas.shp")
elif len(shps_finais) == 1:
    arcpy.AddMessage("Apenas 1 ponto — merge nao necessario.")

if arcpy.Exists(pontos_shp):
    arcpy.Delete_management(pontos_shp)

# ============================================================
# PASSO 6 — adiciona camadas ao Table of Contents
# ============================================================

arcpy.AddMessage("Adicionando camadas ao mapa...")

mxd = arcpy.mapping.MapDocument("CURRENT")
df  = arcpy.mapping.ListDataFrames(mxd)[0]

for shp in shps_finais:
    if arcpy.Exists(shp):
        camada = arcpy.mapping.Layer(shp)
        arcpy.mapping.AddLayer(df, camada, "TOP")
        arcpy.AddMessage("  Adicionado: " + os.path.basename(shp))

if bacia_completa and arcpy.Exists(bacia_completa):
    camada_completa = arcpy.mapping.Layer(bacia_completa)
    arcpy.mapping.AddLayer(df, camada_completa, "TOP")
    arcpy.AddMessage("  Adicionado: bacias_todas.shp")

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

# ============================================================
# PASSO 7 — devolve a licenca e finaliza
# ============================================================

arcpy.CheckInExtension("Spatial")

# ============================================================
# PASSO 8 — gera saida para o HidroAPI
# ============================================================

if dados_hidro:
    # Monta texto para colar no campo "Multiplos Pontos" do site
    linhas_hidro = []
    for d in dados_hidro:
        linhas_hidro.append(str(d["lat"]) + "; " + str(d["lon"]) + "; " + str(d["area"]))

    texto_colar = "\n".join(linhas_hidro)

    # Monta URL com parametros
    url_base = "https://SEU-USUARIO.github.io/hidroapi/"
    params_url = "|".join([str(d["lat"]) + "," + str(d["lon"]) + "," + str(d["area"]) for d in dados_hidro])
    url_completa = url_base + "?pontos=" + params_url

    # Salva arquivo TXT na pasta de saida
    arquivo_hidro = os.path.join(pasta_saida, "entrada_hidroapi.txt")
    with open(arquivo_hidro, "w") as f:
        f.write("=" * 55 + "\n")
        f.write("  COPIAR E COLAR NO HIDROAPI\n")
        f.write("  Campo: 'Colar Multiplos Pontos'\n")
        f.write("  Formato: lat; lon; area(km2)\n")
        f.write("=" * 55 + "\n\n")
        f.write(texto_colar)
        f.write("\n\n" + "=" * 55 + "\n")
        f.write("  URL DIRETA (abrir no navegador):\n")
        f.write("=" * 55 + "\n\n")
        f.write(url_completa + "\n")

    arcpy.AddMessage("")
    arcpy.AddMessage("=============================")
    arcpy.AddMessage("PROCESSAMENTO CONCLUIDO")
    arcpy.AddMessage(str(contador) + " bacias delimitadas.")
    arcpy.AddMessage("=============================")
    arcpy.AddMessage("")
    arcpy.AddMessage("╔═══════════════════════════════════════════════════╗")
    arcpy.AddMessage("║  COPIAR E COLAR NO HIDROAPI                      ║")
    arcpy.AddMessage("║  Campo: 'Colar Multiplos Pontos'                 ║")
    arcpy.AddMessage("║  Formato: lat; lon; area(km2)                    ║")
    arcpy.AddMessage("╠═══════════════════════════════════════════════════╣")
    for linha in linhas_hidro:
        arcpy.AddMessage("║  " + linha)
    arcpy.AddMessage("╚═══════════════════════════════════════════════════╝")
    arcpy.AddMessage("")
    arcpy.AddMessage("Arquivo salvo: " + arquivo_hidro)
    arcpy.AddMessage("URL: " + url_completa)
else:
    arcpy.AddMessage("")
    arcpy.AddMessage("=============================")
    arcpy.AddMessage("PROCESSAMENTO CONCLUIDO")
    arcpy.AddMessage(str(contador) + " bacias delimitadas.")
    arcpy.AddMessage("=============================")