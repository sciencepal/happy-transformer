from collections import namedtuple
import torch

SumPair = namedtuple('SumPair',['idx1', 'idx2', 'sum'])

def biggest_sums(items_a, items_b):
    '''
    assumes items_a and items_b sorted (descending)
    return (idx1,idx2,sum) for all the biggest sums
    from items_a and items_b, in decreasing order
    '''
    a_index = b_index = 0
    while a_index < len(items_a) and b_index < len(items_b):
        yield SumPair(
            a_index, b_index,
            sum=items_a[a_index] + items_b[b_index]
        )
        # increment in whichever direction has smaller gain
        # fallback to -inf at end of list. 
        # this will always be taken last.
        next_from_a = items_a[a_index+1] if a_index + 1 < len(items_a) else float('-inf')
        next_from_b = items_b[b_index+1] if b_index + 1 < len(items_b) else float('-inf')

        diff_a = items_a[a_index] - next_from_a
        diff_b = items_b[b_index] - next_from_b

        if diff_a >= diff_b:
            b_index += 1
        else:
            a_index += 1

QaAnswerLogit = namedtuple('QaAnswerLogit', [
    'start_idx','end_idx', 'logit'
])

def qa_logits(start_logits, end_logits):
    sorted_starts_tensors = torch.sort(start_logits, descending=True)
    sorted_ends_tensors = torch.sort(end_logits, descending=True)
    # start logits sorted in descending order INDEPENDENTLY
    sorted_start_scores = sorted_starts_tensors.values.tolist()
    sorted_start_indices = sorted_starts_tensors.indices.tolist()
    # end logits sorted in descending order INDEPENDENTLY
    sorted_end_scores = sorted_ends_tensors.values.tolist()
    sorted_end_indices = sorted_ends_tensors.indices.tolist()
    # start logit + end logit pairs sorted in descending order 
    # of their sum TOGETHER
    all_answers = (
        QaAnswerLogit(
            start_idx=sorted_start_indices[sum_pair.idx1],
            end_idx=sorted_end_indices[sum_pair.idx2],
            logit=sum_pair.sum
        )
        for sum_pair in 
        biggest_sums(sorted_start_scores, sorted_end_scores)
    )
    # filter for only answers which have end after start
    legit_answers = (
        answer
        for answer in all_answers
        if answer.end_idx > answer.start_idx
    )
    return legit_answers

QaProbability = namedtuple('QaProbability', [
    'start_idx', 'end_idx', 'probability'
])
QaAnswer = namedtuple('QaAnswer',[
    'text', 'probability'
])

def qa_probabilities(start_logits, end_logits, k):
    answer_logits_iterator = qa_logits(start_logits, end_logits)
    top_answers = [
        next(answer_logits_iterator)
        for _ in range(k)
    ]
    logit_scores = torch.tensor([
        answer.logit
        for answer in top_answers
    ])

    probabilities = torch.nn.Softmax(dim=0)(logit_scores).tolist()
    # NOTE: throwing away indices. Do we care?
    return [
        QaProbability(
            start_idx=answer.start_idx,
            end_idx=answer.end_idx,
            probability=probability
        )
        for answer, probability in zip(top_answers, probabilities)
    ]