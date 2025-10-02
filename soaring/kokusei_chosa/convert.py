import csv
from collections import defaultdict

target_columns = [
    # "０〜４歳人口総数",
    # "５〜９歳人口総数",
    # "１０〜１４歳人口総数",
    # "１５〜１９歳人口総数",
    # "２０〜２４歳人口総数",
    # "２５〜２９歳人口総数",
    # "３０〜３４歳人口総数",
    # "３５〜３９歳人口総数",
    # "４０〜４４歳人口総数",
    # "４５〜４９歳人口総数",
    # "５０〜５４歳人口総数",
    # "５５〜５９歳人口総数",
    "６０〜６４歳人口総数",
    "６５〜６９歳人口総数",
    "７０〜７４歳人口総数",
    "７５〜７９歳人口総数",
    "８０〜８４歳人口総数",
    "８５〜８９歳人口総数",
    "９０〜９４歳人口総数",
    "９５歳以上人口総数",
]


def main():
    with open("tblT001175Q5740.txt", encoding="shift-jis") as f:
        next(f)
        reader = csv.reader(f)
        print("mesh_key,over60_population")
        for row_index, row in enumerate(reader):
            mesh_key = row[0]
            mesh_sum = 0
            if row_index == 0:
                continue
            for col_index, col in enumerate(row):
                if col_index < 43:
                    continue
                if (col_index - 43) % 3 == 0 and col_index != 67:
                    count = int(col) if col != "*" else 0
                    mesh_sum += count
            print(mesh_key, mesh_sum, sep=",")


if __name__ == "__main__":
    main()
