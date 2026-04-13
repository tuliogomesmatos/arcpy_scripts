# ============================================================
# DELIMITACAO DE BACIAS DE CONTRIBUICAO
# Versao 2.0 — Tool para ArcGIS
# ============================================================

import arcpy
import os

# ============================================================
# ENTRADAS — agora vem da interface da tool
# ============================================================

pontos       = arcpy.GetParameterAsText(0)
accum_to     = arcpy.GetParameterAsText(1)
direct_to    = arcpy.GetParameterAsText(2)
pasta_saida  = arcpy.GetParameterAsText(3)
sistema_ref  = arcpy.GetParameter(4)
# ============================================================
# CONFIGURACOES
# ============================================================

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

# ============================================================
# PASSO 1 — verifica e prepara a pasta de saida
# ============================================================

if not os.path.exists(pasta_saida):
    os.makedirs(pasta_saida)
    arcpy.AddMessage("Pasta de saida criada: " + pasta_saida)
else:
    arcpy.AddMessage("Pasta de saida ja existe: " + pasta_saida)

# ============================================================
# PASSO 2 — resolucao do raster automaticamente
# ============================================================

resolucao_texto = arcpy.GetRasterProperties_management(
    accum_to, "CELLSIZEX").getOutput(0)

resolucao = float(resolucao_texto.replace(",", "."))

snap_distancia = resolucao * 5

arcpy.AddMessage("Resolucao do raster: " + str(resolucao) + " metros")
arcpy.AddMessage("Distancia de snap: " + str(snap_distancia) + " metros")

# ============================================================
# PASSO 3 — quantos pontos serao processados
# ============================================================

total_pontos = int(arcpy.GetCount_management(pontos).getOutput(0))
arcpy.AddMessage("Total de pontos: " + str(total_pontos))

# ============================================================
# PASSO 4 — loop principal
# ============================================================

contador = 0

with arcpy.da.SearchCursor(pontos, ["OID@", "SHAPE@XY"]) as cursor:
    for row in cursor:

        id_ponto    = row[0]
        contador   += 1

        arcpy.AddMessage("")
        arcpy.AddMessage("Processando ponto " + str(contador) + " de " + str(total_pontos))

        # ── 4a — copia o ponto ────────────────────────────────

        ponto_temp = os.path.join(pasta_saida, "ponto_temp_" + str(id_ponto) + ".shp")

        arcpy.Select_analysis(
            pontos,
            ponto_temp,
            '"FID" = ' + str(id_ponto)
        )

        # ── 4b — reprojeta se necessario ──────────────────────

        sr_ponto = arcpy.Describe(ponto_temp).spatialReference

        if sr_ponto.factoryCode != sistema_ref.factoryCode:
            arcpy.AddMessage("  Reprojetando ponto...")
            ponto_proj = os.path.join(pasta_saida, "ponto_proj_" + str(id_ponto) + ".shp")
            arcpy.Project_management(ponto_temp, ponto_proj, sistema_ref)
        else:
            ponto_proj = ponto_temp
            arcpy.AddMessage("  Ponto ja esta na projecao correta.")

        # ── 4c — snap pour point ──────────────────────────────

        arcpy.AddMessage("  Aplicando Snap Pour Point...")

        snap_saida = os.path.join(pasta_saida, "snap_" + str(id_ponto) + ".tif")

        arcpy.gp.SnapPourPoint_sa(
            ponto_proj,
            accum_to,
            snap_saida,
            snap_distancia,
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

        bacia_poligono = os.path.join(pasta_saida, "bacia_" + str(id_ponto) + ".shp")

        arcpy.RasterToPolygon_conversion(
            bacia_raster,
            bacia_poligono,
            "NO_SIMPLIFY",
            "VALUE"
        )

        # ── 4f — dissolve ─────────────────────────────────────

        arcpy.AddMessage("  Dissolvendo...")

        bacia_dissolv = os.path.join(pasta_saida, "bacia_" + str(id_ponto) + "_dissolv.shp")

        arcpy.Dissolve_management(
            bacia_poligono,
            bacia_dissolv
        )

        # ── 4g — reprojetar resultado ─────────────────────────

        arcpy.AddMessage("  Reprojetando resultado...")

        bacia_final = os.path.join(pasta_saida, "bacia_" + str(id_ponto) + "_final.shp")

        arcpy.Project_management(
            bacia_dissolv,
            bacia_final,
            sistema_ref
        )

        # ── 4h — calcular area em km2 ─────────────────────────

        arcpy.AddMessage("  Calculando area...")

        campo_area = "AREA_KM2"

        if campo_area not in [f.name for f in arcpy.ListFields(bacia_final)]:
            arcpy.AddField_management(bacia_final, campo_area, "DOUBLE")

        with arcpy.da.UpdateCursor(bacia_final, ["SHAPE@AREA", campo_area]) as cur_area:
            for linha in cur_area:
                linha[1] = round(linha[0] / 1000000, 4)
                cur_area.updateRow(linha)

        arcpy.AddMessage("  Ponto " + str(id_ponto) + " concluido.")

# ============================================================
# PASSO 5 — merge de todos os resultados
# ============================================================

arcpy.AddMessage("")
arcpy.AddMessage("Juntando resultados...")

bacia_completa = os.path.join(pasta_saida, "bacias_todas.shp")

shps_finais = []
for i in range(total_pontos):
    candidato = os.path.join(pasta_saida, "bacia_" + str(i) + "_final.shp")
    if arcpy.Exists(candidato):
        shps_finais.append(candidato)

if len(shps_finais) > 0:
    arcpy.Merge_management(shps_finais, bacia_completa)
    arcpy.AddMessage("Arquivo final: bacias_todas.shp")

# ============================================================
# PASSO 6 — devolve a licenca e finaliza
# ============================================================

arcpy.CheckInExtension("Spatial")

arcpy.AddMessage("")
arcpy.AddMessage("=============================")
arcpy.AddMessage("PROCESSAMENTO CONCLUIDO")
arcpy.AddMessage(str(contador) + " bacias delimitadas.")
arcpy.AddMessage("=============================")