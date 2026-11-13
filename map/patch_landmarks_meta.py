import json

with open('/Users/nb/google/Antigravity/工作/运营/价单/sandbox/hk_landmarks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 学校属性映射表
# 字段: school_type (官立, 津贴, 直资, 私立, 国际, 公立大学)
# school_type_desc (简明说明)
# school_level (学段年级)
# school_feature (特色/直升)

SCHOOL_TYPE_EXPLAIN = {
    '官立': '政府全资开办与管理，免学费，完全按官立派位机制录取',
    '津贴': '非牟利机构办学、政府全额资助，免学费，按官方校网统一派位',
    '直资': '享有政府津贴并自收学费，课程与招生自主权极高，全港传统顶尖名门集中',
    '私立': '自负盈亏自主办学，全港公开自主面试招生，不受校网户籍限制',
    '国际': '采用全英/双语国际课程(IB/AP/英国体系)，面向海外名校升学，高净值家庭首选',
    '公立大学': '香港教资会(UGC)资助法定八所公立高等学府，国际学术声誉卓越'
}

SCHOOL_MAP = {
    'hku': {'school_type': '公立大学', 'school_level': '本科 / 硕士 / 博士高等教育', 'school_feature': '香港历史最悠久高等学府 · QS世界顶尖名校'},
    'polyu': {'school_type': '公立大学', 'school_level': '本科 / 硕士 / 博士高等教育', 'school_feature': '红磡核心工商与应用科学顶尖名校'},
    'cityu': {'school_type': '公立大学', 'school_level': '本科 / 硕士 / 博士高等教育', 'school_feature': '九龙塘枢纽高校 · 创新科技与国际化商科领先'},
    'hkbu': {'school_type': '公立大学', 'school_level': '本科 / 硕士 / 博士高等教育', 'school_feature': '九龙塘人文名校 · 传理学院享誉亚洲'},
    'cuhk': {'school_type': '公立大学', 'school_level': '本科 / 硕士 / 博士高等教育', 'school_feature': '沙田书院制综合名校 · 诺奖与名学者云集'},
    'hkust': {'school_type': '公立大学', 'school_level': '本科 / 硕士 / 博士高等教育', 'school_feature': '清水湾国际顶尖研究型大学 · 科技商科全球领先'},
    'univ_lingnan': {'school_type': '公立大学', 'school_level': '本科 / 硕士 / 博士高等教育', 'school_feature': '亚洲顶尖博雅大学 · 小班化精致人文社科教育'},
    'univ_eduhk': {'school_type': '公立大学', 'school_level': '本科 / 硕士 / 博士高等教育', 'school_feature': '全港唯一师资培训公立大学 · 教育学科全球前列'},
    'school_dbs': {'school_type': '直资', 'school_level': '中学 (中一至中六)', 'school_feature': '一条龙 (直升拔萃男书院附小) · DSE / IB 双轨顶级男校'},
    'school_dgs': {'school_type': '直资', 'school_level': '中学 (中一至中六)', 'school_feature': '一条龙 (直升拔萃女小学) · 全港顶尖女校神校，状元摇篮'},
    'school_lasalle_col': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '直属喇沙小学 (升中直通) · 九龙塘41校网传奇男校'},
    'school_lasalle_pri': {'school_type': '津贴', 'school_level': '小学 (小一至小六)', 'school_feature': '直属升读喇沙书院 · 41校网首屈一指名牌津贴男小'},
    'school_maryknoll': {'school_type': '津贴', 'school_level': '小学至高中 (小一至中六)', 'school_feature': '直属中小学 · 41校网龙头百年红砖地标女校名门'},
    'school_spcc': {'school_type': '直资', 'school_level': '中学 (中一至中六)', 'school_feature': '一条龙 (直升附小) · 全港IB/DSE双轨常年全港第一神校'},
    'school_spccps': {'school_type': '直资', 'school_level': '小学 (小一至小六)', 'school_feature': '一条龙100%直升圣保罗男女中学 · 全港最高竞争率附小'},
    'school_st_paul_col': {'school_type': '直资', 'school_level': '中学 (中一至中六)', 'school_feature': '直属圣保罗书院小学 · 香港历史最悠久名门直资男校 (1851年创校，全港招生)'},
    'school_queens_col': {'school_type': '官立', 'school_level': '中学 (中一至中六)', 'school_feature': '香港官立男校之首 · 联系轩尼诗道官立小学等，状元辈出'},
    'school_kings_col': {'school_type': '官立', 'school_level': '中学 (中一至中六)', 'school_feature': '港岛11校网传统名门官立男校 · 法定红砖古迹校园'},
    'school_st_paul_convent': {'school_type': '直资', 'school_level': '中学 (中一至中六)', 'school_feature': '直属圣保禄学校小学部 · 铜锣湾核心名门天主教直资女校 (全港招生)'},
    'school_st_stephen_girls': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '直属圣士提反女子中学附小 · 西半山百年名门女校 (11校网)'},
    'school_wah_yan_hk': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '直属番禺会所华仁小学 · 港岛12校网传统天主教名门男校'},
    'school_wah_yan_kln': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '九龙核心名门男校 · 绿树成荫，自由学风与顶尖理科声誉'},
    'school_heep_yunn': {'school_type': '直资', 'school_level': '中学 (中一至中六)', 'school_feature': '联系协恩中学附小 · 何文田顶尖直资名门女校 (全港招生)，文体学业双全'},
    'school_heep_yunn_pri': {'school_type': '津贴', 'school_level': '小学 (小一至小六)', 'school_feature': '联系升读协恩中学 · 34校网首屈一指名牌津贴女小'},
    'school_st_mary': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '直属嘉诺撒圣玛利学校 · 尖沙咀百年法定古迹名门女校'},
    'school_dps': {'school_type': '津贴', 'school_level': '小学 (小一至小六)', 'school_feature': '41校网男女名牌小学 · 享誉九龙塘核心学区'},
    'school_st_joseph': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '直属圣若瑟小学 · 中半山名门天主教喇沙修士会男校'},
    'school_ying_wa': {'school_type': '直资', 'school_level': '中学 (中一至中六)', 'school_feature': '一条龙 (直升英华小学) · 九龙西百年名门直资男校'},
    'school_good_hope': {'school_type': '直资', 'school_level': '中学 (中一至中六)', 'school_feature': '直属德望小学 · 九龙名牌天主教女校，全人教育出众'},
    'school_st_peter_pri': {'school_type': '津贴', 'school_level': '小学 (小一至小六)', 'school_feature': '11校网极具声誉百年名牌津贴小学 · 升中战绩卓著'},
    'school_hennessy_pri': {'school_type': '官立', 'school_level': '小学 (小一至小六)', 'school_feature': '联系皇仁书院与庇理罗士 · 12校网名牌官立小学首选'},
    'school_cis': {'school_type': '国际', 'school_level': '幼小中贯通 (Reception至Year 13)', 'school_feature': '全港顶尖中英双语国际名校 · 全阶段 IB 课程，名校录取率极高'},
    'school_gsis': {'school_type': '国际', 'school_level': '幼小中贯通 (幼稚园至高中)', 'school_feature': '山顶顶奢国际名校 · 学术成绩常年全港第一，德国与英国IB双轨'},
    'school_isf': {'school_type': '私立', 'school_level': '一条龙贯通 (Foundation至Grade 12)', 'school_feature': '薄扶林顶级独立私立名校 · 弘扬中华文化与卓越双语 IB 课程'},
    'school_harrow': {'school_type': '国际', 'school_level': '幼小中贯通 (K1至Year 13)', 'school_feature': '全港唯一纯正英国贵族寄宿制名校 · 英国九大公学传承'},
    'school_hkis': {'school_type': '国际', 'school_level': '幼小中贯通 (Reception 1至Grade 12)', 'school_feature': '全港历史最悠久美制顶尖名校 · 纯正美式 AP 体系直通常春藤'},
    'school_cdnis': {'school_type': '国际', 'school_level': '幼小中贯通 (Early Years至Grade 12)', 'school_feature': '港岛南区全阶段 IB 一条龙国际名校 (PYP/MYP/DP)'},
    'school_sis': {'school_type': '国际', 'school_level': '幼小中贯通 (Preparatory至Year 12)', 'school_feature': '新加坡教育部在港唯一海外名校 · 数理与中英双语顶尖'},
    'school_ycis': {'school_type': '国际', 'school_level': '幼小中贯通 (婴幼儿至Year 13)', 'school_feature': '九龙塘核心知名历史悠久国际学校 · 双校长与双教师国际教学'},
    'school_fis': {'school_type': '国际', 'school_level': '幼小中贯通 (RC至Year 13)', 'school_feature': '全港知名国际学校 · 法国部与国际部(IB DP)双轨制现代化校舍'},
    'school_malvern': {'school_type': '国际', 'school_level': '小学至高中 (Prep 1至Year 13)', 'school_feature': '英国百年贵族学校分校 · 科学园白石角 IB 全阶段现代化名校'},
    'school_vsa': {'school_type': '私立', 'school_level': '一条龙贯通 (Year 1至Year 12)', 'school_feature': '港岛深湾知名双语 IB 贯通名校 · 一条龙直升'},
    'school_rchk': {'school_type': '私立', 'school_level': '一条龙贯通 (Year 1至Year 13)', 'school_feature': '英基ESF旗下私立独立一条龙学校 · 全阶段 IB 课程体系'},
    'school_cais': {'school_type': '国际', 'school_level': '预备班至高中 (Prep至Grade 12)', 'school_feature': '九龙知名国际学校 · 加拿大亚伯达省课程与 AP 体系，蝴蝶谷旗舰校舍'},
    'school_esf_island': {'school_type': '国际', 'school_level': '中学阶段 (Year 7至Year 13)', 'school_feature': '英基ESF旗下历史悠久旗舰名校 · 中半山波老道全新现代化校园'},
    'school_esf_kgv': {'school_type': '国际', 'school_level': '中学阶段 (Year 7至Year 13)', 'school_feature': '何文田英基旗舰百年名校 · IB DP 成绩优异，全人发展'},
    'school_cky': {'school_type': '私立', 'school_level': '一条龙贯通 (Year 1至Year 12)', 'school_feature': '保良局知名非牟利私立名校 · 一条龙双语教学，IB 状元频出'},
    'school_pui_ching': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '联系香港培正小学 · 何文田百年顶流中文名校，丘成桐等泰斗母校'},
    'school_dbspd': {'school_type': '直资', 'school_level': '小学 (小一至小六)', 'school_feature': '一条龙100%直升拔萃男书院 · 全港极抢手顶尖男小，免升中派位'},
    'school_dgjs': {'school_type': '私立', 'school_level': '小学 (小一至小六)', 'school_feature': '一条龙100%直升拔萃女书院 · 全港排名第一私立女校神小'},
    'school_munsang': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '联系民生书院小幼 · 九龙塘41校网百年名校，全港极罕有大校园'},
    'school_ying_wa_primary': {'school_type': '直资', 'school_level': '小学 (小一至小六)', 'school_feature': '一条龙100%直升英华书院 · 西九龙极抢手一条龙直资男小'},
    'school_ktlms': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '联系九龙真光中学附小 · 41校网老牌传统名门基督教女校'},
    'school_wa_ying': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '何文田34校网老牌 Band 1A 传统名门中英文学府'},
    'school_ssc': {'school_type': '直资', 'school_level': '中学 (中一至中六)', 'school_feature': '直属圣士提反书院附小 · 全港占地最大百年寄宿名校，IB/DSE双轨'},
    'school_sjps': {'school_type': '津贴', 'school_level': '小学 (小一至小六)', 'school_feature': '直属升中圣若瑟书院 · 湾仔12校网传统名牌天主教男小'},
    'school_shcc': {'school_type': '津贴', 'school_level': '中学 (中一至中六)', 'school_feature': '直属嘉诺撒圣心学校 · 港岛南区/薄扶林百年修会名门女校'},
    'school_hkuga': {'school_type': '直资', 'school_level': '小学 (小一至小六)', 'school_feature': '一条龙直升港大同学会书院 · 新兴直资神校，免升中派位风险'},
    'school_stamford': {'school_type': '国际', 'school_level': '幼小中贯通 (Pre-K至Grade 12)', 'school_feature': '何文田核心美制 IB 国际学校 · 美式课程标准 + IB DP'},
    'school_aishk': {'school_type': '国际', 'school_level': '幼小中贯通 (Reception至Year 12)', 'school_feature': '九龙塘全港唯一澳洲制国际学校 · 澳制与 IB 双轨认证'},
    'school_ais': {'school_type': '国际', 'school_level': '幼小中贯通 (Early Childhood至Grade 12)', 'school_feature': '九龙塘老牌纯正美制国际学校 · 美式 AP 精英教育'},
    'school_esf_peak': {'school_type': '国际', 'school_level': '小学阶段 (Year 1至Year 6)', 'school_feature': '山顶豪宅圈核心国际小学 · IB PYP，直升英基港岛中学'},
    'school_esf_bradbury': {'school_type': '国际', 'school_level': '小学阶段 (Year 1至Year 6)', 'school_feature': '司徒拔道豪宅圈顶尖国际小学 · IB PYP，直升英基南岛中学'},
    'school_esf_south_island': {'school_type': '国际', 'school_level': '中学阶段 (Year 7至Year 13)', 'school_feature': '深水湾/黄竹坑豪宅圈顶级国际中学 · IB DP 成绩卓越'},
    'school_wycombe_abbey': {'school_type': '私立', 'school_level': '小学阶段 (Year 1至Year 8)', 'school_feature': '英国威雅公学香港私立分校 · 全人英式精英教育直通英美名校'},
    'school_shrewsbury': {'school_type': '国际', 'school_level': '学前至小学 (Nursery至Year 6)', 'school_feature': '英国九大公学思贝礼在港纯小学分校 · 专精幼小阶段教育'},
    'school_nord_anglia': {'school_type': '国际', 'school_level': '幼小中贯通 (Year 1至Year 13)', 'school_feature': '诺德安达国际教育集团 · 茱莉亚学院与麻省理工合作课程，IB DP'}
}

# 商场属性映射表
# 字段: mall_level (全港顶奢旗舰, 区域枢纽旗舰, 潮流艺术地标, 滨海度假街区, 优质社区生活中心)
# mall_scale (商场建筑面积/规模)
# mall_shops (约计店铺数/特色)

MALL_MAP = {
    'mall_ifc': {'mall_level': '全港顶奢旗舰', 'mall_scale': '约 80 万平方呎', 'mall_feature': '汇聚全球一线顶奢名品、连卡佛及多家米其林星级餐厅'},
    'mall_pacific_place': {'mall_level': '全港顶奢旗舰', 'mall_scale': '约 71 万平方呎', 'mall_feature': '金钟四线枢纽上盖，港岛顶级奢华名品与高端酒店群一体'},
    'mall_times_square': {'mall_level': '全港地标商业', 'mall_scale': '约 90 万平方呎', 'mall_feature': '铜锣湾核心客流地标，全港首座垂直式大型购物中心，超230家名店'},
    'mall_hysan': {'mall_level': '潮流艺术地标', 'mall_scale': '约 45 万平方呎', 'mall_feature': '铜锣湾时尚潮流中心，大型诚品书店及年轻国际时尚品牌旗舰'},
    'mall_sogo_cwb': {'mall_level': '全港地标百货', 'mall_scale': '约 40 万平方呎', 'mall_feature': '香港规模最大日式百货店，铜锣湾核心商圈黄金十字路口心脏'},
    'mall_lee_gardens': {'mall_level': '全港顶奢旗舰', 'mall_scale': '约 90 万平方呎 (群楼)', 'mall_feature': '铜锣湾顶级私享名品聚集地，高端亲子生活与米其林尊贵体验'},
    'mall_cityplaza': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 111 万平方呎', 'mall_feature': '港岛东最大型购物综合体，超170间商铺、真雪溜冰场与全功能家庭生活'},
    'mall_southside': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 51 万平方呎', 'mall_feature': '港岛南区全新 TOD 地标商场，黄竹坑站无缝直达，英皇戏院与百间商户'},
    'mall_arcade': {'mall_level': '滨海度假街区', 'mall_scale': '约 27 万平方呎', 'mall_feature': '港岛南区数码港滨海休闲商场，海景全景影院、草坪亲子与特色餐饮'},
    'mall_paradise': {'mall_level': '优质社区生活中心', 'mall_scale': '约 34 万平方呎', 'mall_feature': '港岛东大型运动名牌奥特莱斯与杏花邨上盖核心生活枢纽'},
    'mall_k11_musea': {'mall_level': '全港顶奢旗舰', 'mall_scale': '约 120 万平方呎', 'mall_feature': '维港绝美地标，国际艺术与奢华零售典范，星光大道旁文化零售殿堂'},
    'mall_harbour_city': {'mall_level': '全港顶奢旗舰', 'mall_scale': '约 200 万平方呎', 'mall_feature': '全港规模最大超奢购物中心，广东道一线名牌旗舰街，逾450间名店'},
    'mall_elements': {'mall_level': '全港顶奢旗舰', 'mall_scale': '约 100 万平方呎', 'mall_feature': '九龙站机场快线上盖，金木水火土五行主题，顶级奢华名品与溜冰场'},
    'mall_langham': {'mall_level': '潮流艺术地标', 'mall_scale': '约 60 万平方呎', 'mall_feature': '旺角地标超高层潮流商场，特长通天梯与潮牌圣地，日夜客流极旺'},
    'mall_festival_walk': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 120 万平方呎', 'mall_feature': '九龙塘双铁交汇顶级枢纽商场，超大型室内真雪溜冰场，逾220间商户'},
    'mall_airside': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 70 万平方呎', 'mall_feature': '启德全新绿色生态地标商场，MCL大型影院、宠物友好与逾百家特色餐饮'},
    'mall_twins_sogo': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 110 万平方呎', 'mall_feature': '启德双子塔全新商业地标，涵盖九龙最大日式百货与生活零售娱乐综合体'},
    'mall_moko': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 72 万平方呎', 'mall_feature': '旺角东站上盖核心商场，户外儿童公园、IMAX影院与大型家庭生活综合体'},
    'mall_apm': {'mall_level': '潮流艺术地标', 'mall_scale': '约 63 万平方呎', 'mall_feature': '观塘CBD核心夜行概念潮流商场，直连观塘站，年轻潮牌与深夜餐饮'},
    'mall_olympian': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 80 万平方呎 (1-3期)', 'mall_feature': '奥运站大型高端中产生活综合体，戏院、高端超市与丰富特色餐饮'},
    'mall_v_walk': {'mall_level': '优质社区生活中心', 'mall_scale': '约 30 万平方呎', 'mall_feature': '西九龙南昌双铁交汇上盖全新生活商场，嘉禾戏院与逾150间商户'},
    'mall_the_one': {'mall_level': '潮流艺术地标', 'mall_scale': '约 40 万平方呎', 'mall_feature': '尖沙咀弥敦道垂直潮流商场，全港最高纯零售商场之一，高空景观餐厅'},
    'mall_mira_place': {'mall_level': '潮流艺术地标', 'mall_scale': '约 50 万平方呎', 'mall_feature': '尖沙咀核心时尚服饰与国际美食聚集地，涵盖美丽华广场一期及二期'},
    'mall_megabox': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 110 万平方呎', 'mall_feature': '九龙东巨型家庭娱乐商场，全港最大宜家家居IKEA及国际标准溜冰场'},
    'mall_telford': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 93 万平方呎', 'mall_feature': '九龙湾站上盖全功能大型综合商场，东九龙核心生活购物枢纽'},
    'mall_hollywood': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 56 万平方呎', 'mall_feature': '钻石山双铁交汇枢纽商场，百老汇影院与250余间家庭零售品牌'},
    'mall_dragon_centre': {'mall_level': '优质社区生活中心', 'mall_scale': '约 45 万平方呎', 'mall_feature': '深水埗地标级综合生活商场，室内天马溜冰场与全功能平民生活圈'},
    'mall_the_wai': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 65 万平方呎', 'mall_feature': '大围站上盖全新旗舰枢纽商场，新界东生活新核心，英皇戏院与特色餐饮'},
    'mall_new_town_plaza': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 200 万平方呎 (1-3期)', 'mall_feature': '全港客流量最大商场之一，沙田站无缝直连，超350间店铺与户外乐园'},
    'mall_yoho_mall': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 110 万平方呎', 'mall_feature': '新界西北最大型旗舰购物商场，元朗核心生活圈，IMAX影院与户外绿化街区'},
    'mall_popcorn': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 40 万平方呎', 'mall_feature': '将军澳站上盖核心地标商场，双铁直达，无缝连接将军澳一众高端住宅群'},
    'mall_v_city': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 30 万平方呎', 'mall_feature': '屯门站及轻铁交汇上盖核心大型商场，跨境客运与现代年轻时尚消费枢纽'},
    'mall_dpark': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 63 万平方呎', 'mall_feature': '新界亲子主题大型商场，63万呎家庭购物公园，丰富儿童游乐与家庭业态'},
    'mall_citywalk': {'mall_level': '优质社区生活中心', 'mall_scale': '约 50 万平方呎 (1-2期)', 'mall_feature': '荃湾核心绿色环保概念大型商场，垂直花园露天广场与百老汇影院'},
    'mall_east_point': {'mall_level': '优质社区生活中心', 'mall_scale': '约 40 万平方呎', 'mall_feature': '将军澳坑口站大型综合商场，将军澳最早且最繁华的大型家庭零售商场'},
    'mall_metroplaza': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 54 万平方呎', 'mall_feature': '葵芳站上盖时尚生活商场，露天空中花园、大型美妆区与餐饮露台'},
    'mall_citygate': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 80 万平方呎', 'mall_feature': '全港最大名牌奥特莱斯折扣商场，东涌站上盖，逾150个国际知名品牌常年折让'},
    'mall_landmark': {'mall_level': '全港顶奢旗舰', 'mall_scale': '约 50 万平方呎 (核心裙楼)', 'mall_feature': '中环顶级奢华名品圣地，汇聚全球顶级品牌全球旗舰与米其林三星餐饮'},
    'mall_lee_tung': {'mall_level': '滨海度假街区', 'mall_scale': '约 8.8 万平方呎', 'mall_feature': '湾仔特色欧式林荫商业步行街，露天咖啡座、特色餐饮与品质生活慢调街区'},
    'mall_hopewell': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 100 万平方呎', 'mall_feature': '湾仔皇后大道东百万呎全新旗舰综合体，全港岛最大零售娱乐休闲新中心'},
    'mall_windsor': {'mall_level': '优质社区生活中心', 'mall_scale': '约 31 万平方呎', 'mall_feature': '铜锣湾告士打道潮流与亲子综合商场，皇室戏院与大型儿童生活专门店'},
    'mall_wtc': {'mall_level': '潮流艺术地标', 'mall_scale': '约 28 万平方呎', 'mall_feature': '铜锣湾告士打道临海时尚购物中心，海景特色餐厅与现代潮流零售'},
    'mall_stanley': {'mall_level': '滨海度假街区', 'mall_scale': '约 10 万平方呎', 'mall_feature': '港岛南区海滨度假风情地标商场，宠物友好海景露台与美美海滨广场'},
    'mall_the_pulse': {'mall_level': '滨海度假街区', 'mall_scale': '约 16.7 万平方呎', 'mall_feature': '全港最美浅水湾滩畔奢华休闲商场，海景屋顶露台、高端餐饮与海滩度假生活'},
    'mall_peak_galleria': {'mall_level': '滨海度假街区', 'mall_scale': '约 13 万平方呎', 'mall_feature': '太平山顶地标观景商场，观景台俯瞰维港全景，特色文创与高空餐饮'},
    'mall_westwood': {'mall_level': '优质社区生活中心', 'mall_scale': '约 24 万平方呎', 'mall_feature': '港岛中西区宝翠园上盖核心家庭生活商场，大型超市及一站式生活服务'},
    'mall_1881': {'mall_level': '全港顶奢旗舰', 'mall_scale': '约 13 万平方呎', 'mall_feature': '尖沙咀前水警总部百年维多利亚古迹名品殿堂，国际顶级名表珠宝聚集地'},
    'mall_k11_art': {'mall_level': '潮流艺术地标', 'mall_scale': '约 34 万平方呎', 'mall_feature': '尖沙咀河内道核心艺术潮流商场，年轻潮牌聚集地、当代艺术展览与特色餐饮'},
    'mall_isquare': {'mall_level': '潮流艺术地标', 'mall_scale': '约 46 万平方呎', 'mall_feature': '尖沙咀弥敦道直连港铁巨型垂直商业，IMAX影院与高空维港景观餐厅'},
    'mall_chkc': {'mall_level': '优质社区生活中心', 'mall_scale': '约 30 万平方呎', 'mall_feature': '尖沙咀中港客运码头上盖金色地标，跨境枢纽与名牌奥特莱斯折扣店'},
    'mall_top_mongkok': {'mall_level': '潮流艺术地标', 'mall_scale': '约 11 万平方呎', 'mall_feature': '旺角弥敦道地铁上盖极具活力的年轻人潮流圣地，韩国流行服饰与特色轻食'},
    'mall_ym2': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 20 万平方呎', 'mall_feature': '观塘市中心大型重建旗舰 TOD 枢纽商场，全港最大室内冷气公共交通交汇处'},
    'mall_domain': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 45 万平方呎', 'mall_feature': '油塘港铁交汇站上盖45万呎旗舰综合体，覆盖油塘一众核心新盘与家庭配套'},
    'mall_mikiki': {'mall_level': '优质社区生活中心', 'mall_scale': '约 21 万平方呎', 'mall_feature': '启德河畔新蒲岗核心品质商场，宠物友好环境与年轻家庭生活配套'},
    'mall_park_central': {'mall_level': '优质社区生活中心', 'mall_scale': '约 40 万平方呎', 'mall_feature': '将军澳站天桥直连大型家庭亲子生活商场，近200间店铺与亲子游乐区'},
    'mall_monterey_place': {'mall_level': '滨海度假街区', 'mall_scale': '约 14 万平方呎', 'mall_feature': '将军澳南滨海长廊中产休闲街区，海景露天餐饮、宠物友好与品质生活步道'},
    'mall_maritime_square': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 58 万平方呎 (1-2期)', 'mall_feature': '青衣站机场快线与东涌线上盖枢纽商场，近百家店铺与影院，交通极为便利'},
    'mall_tmtplaza': {'mall_level': '区域枢纽旗舰', 'mall_scale': '约 100 万平方呎 (1-3期)', 'mall_feature': '新界西北最大型百货综合商场，超百万呎客流核心，逾400家商铺与嘉禾影院'},
    'mall_citylink': {'mall_level': '优质社区生活中心', 'mall_scale': '约 10 万平方呎', 'mall_feature': '沙田站东铁线上盖无缝连接商业中心，通勤人流必经之地与生活零售配套'}
}

# 遍历打标补全
schools_matched = 0
malls_matched = 0

for item in data:
    cid = item.get('id')
    cat = item.get('category')
    
    if cat in ['famous_school', 'university'] or cid in SCHOOL_MAP:
        if cid in SCHOOL_MAP:
            m = SCHOOL_MAP[cid]
            item['school_type'] = m['school_type']
            item['school_type_desc'] = SCHOOL_TYPE_EXPLAIN.get(m['school_type'], '')
            item['school_level'] = m['school_level']
            item['school_feature'] = m['school_feature']
            schools_matched += 1
        else:
            print('School NOT matched:', cid, item.get('name'))
            
    elif cat == 'shopping_mall' or cid in MALL_MAP:
        if cid in MALL_MAP:
            m = MALL_MAP[cid]
            item['mall_level'] = m['mall_level']
            item['mall_scale'] = m['mall_scale']
            item['mall_feature'] = m['mall_feature']
            malls_matched += 1
        else:
            print('Mall NOT matched:', cid, item.get('name'))

print(f"Total schools successfully patched: {schools_matched}/{len([x for x in data if x.get('category') in ['famous_school', 'university']])}")
print(f"Total malls successfully patched: {malls_matched}/{len([x for x in data if x.get('category') == 'shopping_mall'])}")

# 写入更新后的 json
with open('/Users/nb/google/Antigravity/工作/运营/价单/sandbox/hk_landmarks.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("hk_landmarks.json successfully updated!")
