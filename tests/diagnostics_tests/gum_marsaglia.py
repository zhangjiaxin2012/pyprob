import pyprob
import pyprob.diagnostics
import torch
import math
import os
import shutil
from pyprob import Model, InferenceEngine
from pyprob.distributions import Uniform, Normal


class GaussianWithUnknownMeanMarsaglia(Model):
    def __init__(self, prior_mean=1, prior_stddev=math.sqrt(5), likelihood_stddev=math.sqrt(2)):
        self.prior_mean = prior_mean
        self.prior_stddev = prior_stddev
        self.likelihood_stddev = likelihood_stddev
        super().__init__('Gaussian with unknown mean (Marsaglia)')

    def marsaglia(self, mean, stddev):
        uniform = Uniform(-1, 1)
        s = 1
        while float(s) >= 1:
            x = pyprob.sample(uniform, replace=True)
            y = pyprob.sample(uniform, replace=True)
            s = x*x + y*y
        return mean + stddev * (x * torch.sqrt(-2 * torch.log(s) / s))

    def forward(self):
        mu = self.marsaglia(self.prior_mean, self.prior_stddev)
        likelihood = Normal(mu, self.likelihood_stddev)
        pyprob.tag(mu, name='mu')
        pyprob.observe(likelihood, name='obs0')
        pyprob.observe(likelihood, name='obs1')
        return mu


if __name__ == '__main__':
    pyprob.set_random_seed(123)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    print('Current dir: {}'.format(current_dir))
    model = GaussianWithUnknownMeanMarsaglia()
    num_traces = 2000

    ground_truth_trace = next(model._trace_generator(inference_engine=InferenceEngine.RANDOM_WALK_METROPOLIS_HASTINGS))
    observes = {'obs0': ground_truth_trace.named_variables['obs0'].value, 'obs1': ground_truth_trace.named_variables['obs1'].value}

    posteriors_dir = os.path.join(current_dir, 'posteriors')
    shutil.rmtree(posteriors_dir)
    pyprob.util.create_path(posteriors_dir, directory=True)

    posterior_is_file_name = os.path.join(posteriors_dir, 'posterior_is')
    posterior_is = model.posterior_traces(num_traces, inference_engine=InferenceEngine.IMPORTANCE_SAMPLING, observe=observes, file_name=posterior_is_file_name)
    proposal_is = posterior_is.unweighted().rename(posterior_is.name.replace('Posterior', 'Proposal'))

    posterior_rmh_file_name = os.path.join(posteriors_dir, 'posterior_rmh')
    posterior_rmh = model.posterior_traces(num_traces, inference_engine=InferenceEngine.RANDOM_WALK_METROPOLIS_HASTINGS, observe=observes, file_name=posterior_rmh_file_name)

    posterior_rmh_autocorrelation_file_name = os.path.join(posteriors_dir, 'posterior_rmh_autocorrelation')
    pyprob.diagnostics.autocorrelations(posterior_rmh, n_most_frequent=50, plot=True, plot_show=False, file_name=posterior_rmh_autocorrelation_file_name)

    posterior_rmh_gt_file_name = os.path.join(posteriors_dir, 'posterior_rmh_gt')
    posterior_rmh_gt = model.posterior_traces(num_traces, inference_engine=InferenceEngine.RANDOM_WALK_METROPOLIS_HASTINGS, observe=observes, initial_trace=ground_truth_trace, file_name=posterior_rmh_gt_file_name)

    posterior_rmh_gr_file_name = os.path.join(posteriors_dir, 'posterior_rmh_gelman_rubin')
    pyprob.diagnostics.gelman_rubin([posterior_rmh, posterior_rmh_gt], n_most_frequent=50, plot=True, plot_show=False, file_name=posterior_rmh_gr_file_name)

    posterior_rmh_log_prob_file_name = os.path.join(posteriors_dir, 'posterior_rmh_log_prob')
    pyprob.diagnostics.log_prob([posterior_rmh, posterior_rmh_gt], plot=True, plot_show=False, file_name=posterior_rmh_log_prob_file_name)

    posterior_rmh_addresses_file_name = os.path.join(posteriors_dir, 'posterior_rmh_addresses')
    pyprob.diagnostics.address_histograms([proposal_is, posterior_is, posterior_rmh], plot=True, plot_show=False, ground_truth_trace=ground_truth_trace, file_name=posterior_rmh_addresses_file_name)

    posterior_is.close()
    posterior_rmh.close()
    posterior_rmh_gt.close()
    print('Done')
