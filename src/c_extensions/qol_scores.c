#include <stddef.h>

int is_nan(double value) {
    return value != value;
}

void compute_quality_scores(
    const double *features,
    const double *weights,
    size_t n_samples,
    size_t n_features,
    double *out_scores
) {
    for (size_t i = 0; i < n_samples; ++i) {
        double acc = 0.0;
        const double *row = features + (i * n_features);
        for (size_t j = 0; j < n_features; ++j) {
            double v = row[j];
            if (is_nan(v)) {
                continue;
            }
            acc += v * weights[j];
        }
        out_scores[i] = acc;
    }
}
