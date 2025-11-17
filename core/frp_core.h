#pragma once

#ifdef _WIN32
#ifdef FRP_CORE_EXPORTS
#define FRP_API __declspec(dllexport)
#else
#define FRP_API __declspec(dllimport)
#endif
#else
#define FRP_API
#endif

extern "C"
{

    struct FrpResult
    {
        double outer_diameter_avg;
        double inner_diameter_avg;
        double roundness_outer;
        double roundness_inner;
        double straightness;
        double concentricity;
        double length;
        int ok_flag; // 1 = OK, 0 = NG
    };

    // 初始化一次
    FRP_API void frp_init();

    // 清空当前测量数据
    FRP_API void frp_reset();

    // 每采到一个点就调用一次（示例：角度 + 内外径）
    FRP_API void frp_add_sample(double angle_deg,
                                double outer_d_mm,
                                double inner_d_mm);

    // 计算结果，填充到 result 里
    FRP_API void frp_compute(FrpResult *result);
}
