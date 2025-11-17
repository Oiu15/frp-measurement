#define FRP_CORE_EXPORTS
#include "frp_core.h"
#include <vector>
#include <cmath>

static std::vector<double> g_outer;
static std::vector<double> g_inner;

extern "C"
{

    FRP_API void frp_init()
    {
        g_outer.clear();
        g_inner.clear();
    }

    FRP_API void frp_reset()
    {
        g_outer.clear();
        g_inner.clear();
    }

    FRP_API void frp_add_sample(double angle_deg,
                                double outer_d_mm,
                                double inner_d_mm)
    {
        (void)angle_deg; // demo 里暂时不用
        g_outer.push_back(outer_d_mm);
        g_inner.push_back(inner_d_mm);
    }

    static double avg(const std::vector<double> &v)
    {
        if (v.empty())
            return 0.0;
        double s = 0.0;
        for (double x : v)
            s += x;
        return s / v.size();
    }

    FRP_API void frp_compute(FrpResult *result)
    {
        if (!result)
            return;
        result->outer_diameter_avg = avg(g_outer);
        result->inner_diameter_avg = avg(g_inner);
        // 下面这些先随便给个假值，方便联调 UI
        result->roundness_outer = 0.03;
        result->roundness_inner = 0.02;
        result->straightness = 0.01;
        result->concentricity = 0.05;
        result->length = 1.8;
        result->ok_flag = 1;
    }
}
